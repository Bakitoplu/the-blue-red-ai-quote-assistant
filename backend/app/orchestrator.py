from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta
from collections.abc import Iterator
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .models import ChatMessage, ChatSession, KnowledgeEntry, PendingAction, PriceRule, Product, Quote, ToolCallLog
from .schemas import (
    AddToQuoteRequest,
    ChatStreamRequest,
    KnowledgeRequest,
    ProductFilters,
    ReplaceWithAlternativeRequest,
    SearchProductsRequest,
    UpdateQuoteItemRequest,
)
from .tools import add_to_quote, get_knowledge_entries, get_quote, replace_with_alternative, search_products, update_quote_item


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _norm(text: str) -> str:
    text = text.casefold().replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _price_limit(text: str) -> float | None:
    ntext = _norm(text)
    bin_match = re.search(r"(\d+(?:[.,]\d+)?)\s*bin\s*(?:tl|try)?", ntext)
    if bin_match:
        return float(bin_match.group(1).replace(",", ".")) * 1000
    match = re.search(r"(\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(?:tl|try)", ntext)
    if not match:
        return None
    return float(match.group(1).replace(".", "").replace(" ", ""))


def _is_confirmation(text: str) -> bool:
    n = _norm(text)
    return any(re.search(rf"\b{word}\b", n) for word in ["evet", "tamam", "onayliyorum", "ekle", "uygula", "olur"])


def _is_cancel(text: str) -> bool:
    n = _norm(text)
    return any(re.search(rf"\b{word}\b", n) for word in ["hayir", "iptal", "vazgec", "ekleme", "istemiyorum"])


def _allow_wait(text: str) -> bool:
    n = _norm(text)
    return any(phrase in n for phrase in ["bekleyebilirim", "stok gelince", "beklemeli", "on siparis", "ön sipariş"])


def _is_product_question(text: str) -> bool:
    n = _norm(text)
    if any(k in n for k in ["ekle", "ekler", "teklife koy", "teklifime koy", "degistir", "değiştir", "cikar", "çıkar"]):
        return False
    question_terms = ["fiyati", "fiyat", "stokta", "var mi", "destekli", "garantisi", "garanti", "kac ay", "kac gunde", "teslim", "nedir", "ne kadar", "alternatifi"]
    product_terms = ["prd-", "bluescan", "redscan", "blueprint", "koruyucu", "arac sarj", "usb-c", "fis yazici", "barkod okuyucu"]
    return any(p in n for p in product_terms) and any(q in n for q in question_terms)


def _is_recommendation_only(text: str) -> bool:
    n = _norm(text)
    return any(k in n for k in ["oner", "öner", "uygun urun", "uygun ürün", "tavsiye", "hangisini"]) and "ekle" not in n


def _is_smalltalk(text: str) -> bool:
    n = _norm(text)
    return any(phrase in n for phrase in ["merhaba", "selam", "nasilsin", "ne yapabilirsin", "yardim"])


def _has_business_signal(text: str) -> bool:
    n = _norm(text)
    signals = [
        "prd-",
        "bluescan",
        "redscan",
        "blueprint",
        "teklif",
        "urun",
        "ürün",
        "stok",
        "fiyat",
        "garanti",
        "teslim",
        "indirim",
        "kurulum",
        "lisans",
        "barkod",
        "qr",
        "yazici",
        "yazıcı",
        "sarj",
        "şarj",
        "iade",
    ]
    return any(signal in n for signal in signals)


def _select_product_for_question(text: str, products: list[dict]) -> dict | None:
    n = _norm(text)
    preferred = None
    if "prd-bc-110" in n or "bluescan air" in n:
        preferred = "PRD-BC-110"
    elif "redscan mini" in n:
        preferred = "PRD-BC-130"
    elif "koruyucu" in n or "silikon kilif" in n:
        preferred = "PRD-ACC-710"
    elif "arac sarj" in n:
        preferred = "PRD-ACC-730"
    elif "blueprint 80" in n or "ethernet fis" in n:
        preferred = "PRD-PRN-320"
    if preferred:
        for product in products:
            if product["product_id"] == preferred:
                return product
    return products[0] if products else None


def _source_label(db: Session, source_id: str) -> str:
    if source_id.startswith("PRD-"):
        product = db.get(Product, source_id)
        return product.name_tr if product else source_id
    if source_id.startswith("KNE-"):
        entry = db.get(KnowledgeEntry, source_id)
        return entry.title if entry else source_id
    if source_id.startswith("RUL-"):
        rule = db.get(PriceRule, source_id)
        return rule.name if rule else "Uygulanan indirim kuralı"
    return source_id


def _quantity(text: str, default: int = 1) -> int:
    words = {"bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4, "beş": 5, "bes": 5}
    ntext = _norm(text)
    m = re.search(r"(\d+)\s*(?:adet|adede|tane|lokasyon)", ntext)
    if m:
        return int(m.group(1))
    for word, value in words.items():
        if re.search(rf"\b{re.escape(word)}\b", ntext):
            return value
    return default


def _topic(text: str) -> str | None:
    n = _norm(text)
    if any(k in n for k in ["iade", "aktiv"]):
        return "return_policy"
    if any(k in n for k in ["teslimat", "sevk"]):
        return "delivery_policy"
    if any(k in n for k in ["garanti"]):
        return "warranty"
    if any(k in n for k in ["indirim", "partner", "hacim"]):
        return "discount_policy"
    if any(k in n for k in ["stok", "stokta olmayan", "bekle"]):
        return "stock_rule"
    if any(k in n for k in ["kurulum", "servis", "lokasyon", "izmir", "yarin", "yarına"]):
        return "service_policy"
    if any(k in n for k in ["offline", "4g", "senkron", "internet olmayacak", "uyuml"]):
        return "compatibility"
    return None


def _search_query(text: str) -> str:
    n = _norm(text)
    if "redscan mini" in n or "cep tipi" in n:
        return "RedScan Mini cep tipi okuyucu"
    if "rugged" in n:
        return "rugged okuyucu"
    if "kablosuz" in n or "qr" in n or "bluescan air" in n:
        return "BlueScan Air kablosuz QR barkod okuyucu"
    if "4g" in n:
        return "4g el terminali"
    if "offline" in n:
        return "offline stok lisansı"
    if "şube" in n or "sube" in n:
        return "şube senkron"
    if "ethernet" in n or "fiş yazıcı" in n or "fis yazici" in n:
        return "ethernet fiş yazıcı"
    if "koruyucu" in n or "kılıf" in n or "kilif" in n:
        return "koruyucu kılıf"
    if "araç şarj" in n or "arac sarj" in n:
        return "araç şarj"
    if "usb-c" in n:
        return "USB-C hızlı şarj"
    if "kurulum" in n:
        return "yerinde kurulum"
    return text


def _log_tool(db: Session, session_id: str, message_id: str, sequence_no: int, tool_name: str, input_json: dict, result, quote_id: str | None):
    log = ToolCallLog(
        session_id=session_id,
        message_id=message_id,
        sequence_no=sequence_no,
        tool_name=tool_name,
        input_json=input_json,
        output_json=result.data if isinstance(result.data, dict) else {"items": result.data},
        success=True,
        source_ids=result.source_ids,
        quote_id=quote_id,
        quote_delta=result.quote_delta,
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return log


def _log_tool_error(db: Session, session_id: str, message_id: str, sequence_no: int, tool_name: str, input_json: dict, quote_id: str | None, error: Exception):
    log = ToolCallLog(
        session_id=session_id,
        message_id=message_id,
        sequence_no=sequence_no,
        tool_name=tool_name,
        input_json=input_json,
        output_json={},
        success=False,
        error=str(error),
        source_ids=[],
        quote_id=quote_id,
        quote_delta={},
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


class ToolRunner:
    def __init__(self, db: Session, session_id: str, message_id: str, quote_id: str):
        self.db = db
        self.session_id = session_id
        self.message_id = message_id
        self.quote_id = quote_id
        self.sequence = 0
        self.sources: list[str] = []
        self.events: list[str] = []

    def run(self, name: str, payload: dict):
        self.sequence += 1
        self.events.append(sse("tool_call_start", {"tool_name": name, "input": payload, "sequence_no": self.sequence}))
        try:
            if name == "search_products":
                result = search_products(self.db, SearchProductsRequest(**payload))
            elif name == "get_knowledge_entries":
                result = get_knowledge_entries(self.db, KnowledgeRequest(**payload))
            elif name == "get_quote":
                result = get_quote(self.db, payload["quote_id"])
            elif name == "add_to_quote":
                result = add_to_quote(self.db, AddToQuoteRequest(**payload))
            elif name == "update_quote_item":
                result = update_quote_item(self.db, UpdateQuoteItemRequest(**payload))
            elif name == "replace_with_alternative":
                result = replace_with_alternative(self.db, ReplaceWithAlternativeRequest(**payload))
            else:
                raise ValueError(f"Bilinmeyen tool: {name}")
        except Exception as exc:
            _log_tool_error(self.db, self.session_id, self.message_id, self.sequence, name, payload, self.quote_id, exc)
            self.events.append(sse("tool_call_result", {"tool_name": name, "success": False, "sequence_no": self.sequence, "error": str(exc)}))
            raise
        _log_tool(self.db, self.session_id, self.message_id, self.sequence, name, payload, result, self.quote_id)
        self.sources.extend(result.source_ids)
        self.events.append(
            sse(
                "tool_call_result",
                {"tool_name": name, "success": True, "sequence_no": self.sequence, "quote_delta": result.quote_delta, "replayed": result.replayed},
            )
        )
        for source in result.source_ids:
            self.events.append(sse("source", {"source_id": source, "label": _source_label(self.db, source)}))
        return result


def _add_key(message_id: str, product_id: str) -> str:
    return f"{message_id}:add:{product_id}"


def _replace_key(message_id: str, from_product_id: str, to_product_id: str) -> str:
    return f"{message_id}:replace:{from_product_id}:{to_product_id}"


def _latest_pending(db: Session, session_id: str, quote_id: str) -> PendingAction | None:
    return db.scalar(
        select(PendingAction)
        .where(PendingAction.session_id == session_id, PendingAction.quote_id == quote_id, PendingAction.status == "pending")
        .order_by(PendingAction.created_at.desc())
    )


def _save_pending(
    db: Session,
    session_id: str,
    quote: Quote,
    action_type: str,
    source_ids: list[str],
    product_id: str | None = None,
    from_product_id: str | None = None,
    to_product_id: str | None = None,
    quantity: int = 1,
    max_price_try: float | None = None,
    allow_wait: bool = False,
) -> PendingAction:
    existing = _latest_pending(db, session_id, quote.quote_id)
    if existing:
        existing.status = "cancelled"
    pending = PendingAction(
        session_id=session_id,
        quote_id=quote.quote_id,
        customer_id=quote.customer_id,
        action_type=action_type,
        product_id=product_id,
        from_product_id=from_product_id,
        to_product_id=to_product_id,
        quantity=quantity,
        max_price_try=max_price_try,
        allow_wait=allow_wait,
        source_ids=list(dict.fromkeys(source_ids)),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.add(pending)
    db.commit()
    return pending


def _compose_text(actions: list[str], sources: list[str], fallback_note: bool) -> str:
    prefix = "Yedek modda kaynaklara göre: " if fallback_note else ""
    return prefix + " ".join(actions)


def _llm_rewrite(settings, user_message: str, draft: str, source_ids: list[str]) -> str:
    if not settings.llm_enabled or not settings.openai_api_key:
        return draft
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Türkçe B2B teklif asistanısın. Sadece verilen taslak ve kaynak ID'lerine dayan. "
                    "Yeni fiyat, stok, teslimat, garanti, politika veya ürün uydurma. "
                    "Teklif mutasyonu, onay ve güvenlik kararlarını değiştirme. Kısa ve net yaz."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "kullanici_mesaji": user_message,
                        "taslak_cevap": draft,
                        "kaynak_idleri": list(dict.fromkeys(source_ids)),
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.2,
    }
    try:
        with httpx.Client(timeout=8) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        return content or draft
    except Exception:
        return draft


def plan_and_execute(db: Session, req: ChatStreamRequest) -> Iterator[str]:
    quote = db.get(Quote, req.quote_id)
    if not quote:
        yield sse("controlled_error", {"error": "Teklif bulunamadı."})
        return
    if req.customer_id and quote.customer_id != req.customer_id:
        yield sse("controlled_error", {"error": "Teklif bu müşteriye ait değil."})
        return
    session_id = req.session_id or f"SES-{uuid4().hex[:10]}"
    message_id = req.message_id or f"MSG-{uuid4().hex[:10]}"
    db.merge(ChatSession(session_id=session_id, quote_id=req.quote_id, customer_id=req.customer_id or quote.customer_id, channel=req.channel))
    db.merge(ChatMessage(message_id=message_id, session_id=session_id, role="user", content=req.message))
    db.commit()
    runner = ToolRunner(db, session_id, message_id, req.quote_id)
    yield sse("message_start", {"session_id": session_id, "message_id": message_id})

    n = _norm(req.message)
    fallback_note = False
    settings = get_settings()
    llm_unavailable = (not settings.llm_enabled) or (not settings.openai_api_key)
    actions: list[str] = []

    try:
        topic = _topic(req.message)
        pending = _latest_pending(db, session_id, req.quote_id)
        if req.require_confirmation and pending and _is_cancel(req.message):
            pending.status = "cancelled"
            db.commit()
            actions.append("Bekleyen işlem iptal edildi; teklif üzerinde değişiklik yapılmadı.")
        elif req.require_confirmation and pending and _is_confirmation(req.message):
            if pending.action_type == "add":
                runner.run(
                    "add_to_quote",
                    {
                        "quote_id": pending.quote_id,
                        "product_id": pending.product_id,
                        "quantity": pending.quantity,
                        "idempotency_key": _add_key(message_id, pending.product_id or ""),
                        "source_message_id": message_id,
                        "allow_wait": pending.allow_wait,
                        "max_price_try": float(pending.max_price_try) if pending.max_price_try is not None else None,
                    },
                )
                pending.status = "applied"
                db.commit()
                runner.run("get_quote", {"quote_id": req.quote_id})
                actions.append("Onayladığınız ürün teklifinize eklendi.")
            else:
                actions.append("Bu bekleyen işlem tipi için uygulama desteği yok; teklif değişmedi.")
        elif req.require_confirmation and _is_confirmation(req.message) and not pending:
            actions.append("Onaylayabileceğim bekleyen bir işlem bulamadım. Ürün veya teklif isteğinizi kısaca yazabilirsiniz.")
        elif req.require_confirmation and _is_smalltalk(req.message):
            actions.append("Merhaba. Ürün, stok, fiyat, garanti, teslimat veya açık teklifiniz hakkında kaynaklı cevap verebilirim.")
        elif req.require_confirmation and _is_product_question(req.message):
            search = runner.run("search_products", {"query": _search_query(req.message), "locale": "tr", "filters": {"in_stock_only": False}, "limit": 5})
            product = _select_product_for_question(req.message, search.data)
            if "garanti" in n and product:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "warranty", "limit": 1})
            if ("teslim" in n or "kac gunde" in n) and product:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "delivery_policy", "limit": 1})
            if ("stokta" in n or "stok" in n) and product and product["stock_qty"] == 0:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "stock_rule", "limit": 1})
            if product:
                qr_text = " QR/2D desteği var." if "qr" in product.get("tags", []) or "2d" in product.get("tags", []) else ""
                actions.append(
                    f"{product['name_tr']} için katalog bilgisi: fiyat {product['price_try']:.0f} TL, stok {product['stock_qty']} adet, "
                    f"garanti {product['warranty_months']} ay, teslimat {product['delivery_days']} gün.{qr_text}"
                )
            else:
                actions.append("Bu bilgi ürün kataloğunda bulunmuyor.")
        elif req.require_confirmation and (_is_recommendation_only(req.message) or "ekle" in n) and ("kablosuz" in n or "qr" in n or "barkod okuyucu" in n):
            limit = _price_limit(req.message)
            search = runner.run("search_products", {"query": "BlueScan Air kablosuz QR barkod okuyucu", "locale": "tr", "filters": {"max_price_try": limit, "in_stock_only": True}, "limit": 5})
            candidates = [item for item in search.data if item["stock_qty"] > 0 and (limit is None or item["price_try"] <= limit)]
            if not candidates:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "price_ceiling", "limit": 1})
                limit_text = f"{int(limit):,}".replace(",", ".") if limit is not None else "belirttiğiniz limit"
                actions.append(f"{limit_text} TL altında stokta kablosuz QR barkod okuyucu bulamadım.")
            else:
                product = candidates[0]
                _save_pending(
                    db,
                    session_id,
                    quote,
                    "add",
                    runner.sources,
                    product_id=product["product_id"],
                    quantity=_quantity(req.message),
                    max_price_try=limit,
                    allow_wait=_allow_wait(req.message),
                )
                actions.append(
                    f"Uygun ürün buldum: {product['name_tr']}. Fiyatı {product['price_try']:.0f} TL, stok {product['stock_qty']} adet. "
                    "Bu ürünü teklifinize eklememi ister misiniz?"
                )
        elif "redscan mini" in n or ("cep tipi" in n and "değiştir" not in n and "degistir" not in n):
            runner.run("search_products", {"query": "RedScan Mini", "locale": "tr", "filters": {"in_stock_only": False}, "limit": 3})
            runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "stock_rule", "limit": 1})
            actions.append("RedScan Mini stokta olmadığı için açık bekleme onayı olmadan teklife eklenmedi; stok kuralı kaynaklandı.")
        elif "çok pahalı" in n or "cok pahali" in n:
            runner.run("get_quote", {"quote_id": req.quote_id})
            limit = _price_limit(req.message)
            runner.run("search_products", {"query": "kablosuz okuyucu", "locale": "tr", "filters": {"max_price_try": limit, "in_stock_only": True}, "limit": 5})
            runner.run("replace_with_alternative", {"quote_id": req.quote_id, "from_product_id": "PRD-BC-120", "to_product_id": "PRD-BC-110", "quantity": None, "reason": "Fiyat limiti altında stoklu alternatif", "idempotency_key": _replace_key(message_id, "PRD-BC-120", "PRD-BC-110"), "max_price_try": limit})
            runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "price_ceiling", "limit": 1})
            actions.append("Pahalı rugged okuyucu pasifleştirildi ve fiyat limitinin altındaki BlueScan Air aktif kalem olarak eklendi.")
        elif "stokta olmayan cep" in n or "uygun stoklu alternatif" in n:
            runner.run("get_quote", {"quote_id": req.quote_id})
            runner.run("search_products", {"query": "cep tipi okuyucu", "locale": "tr", "filters": {"in_stock_only": True}, "limit": 5})
            runner.run("replace_with_alternative", {"quote_id": req.quote_id, "from_product_id": "PRD-BC-130", "to_product_id": "PRD-BC-140", "quantity": None, "reason": "Stoklu alternatif", "idempotency_key": _replace_key(message_id, "PRD-BC-130", "PRD-BC-140")})
            runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "stock_rule", "limit": 1})
            actions.append("Stok dışı cep tipi okuyucu değiştirildi; miktar korunarak GreenScan Eco aktif hale getirildi.")
        elif "mobil bluetooth yazıcı" in n or "mobil bluetooth yazici" in n:
            runner.run("get_quote", {"quote_id": req.quote_id})
            runner.run("search_products", {"query": "fiş yazıcı", "locale": "tr", "filters": {"in_stock_only": True}, "limit": 5})
            runner.run("replace_with_alternative", {"quote_id": req.quote_id, "from_product_id": "PRD-PRN-330", "to_product_id": "PRD-PRN-320", "quantity": None, "reason": "Stoklu Ethernet fiş yazıcı alternatifi", "idempotency_key": _replace_key(message_id, "PRD-PRN-330", "PRD-PRN-320")})
            runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "stock_rule", "limit": 1})
            actions.append("Stok dışı mobil yazıcı pasifleştirildi ve stoklu Ethernet fiş yazıcı eklendi.")
        elif "araç şarj" in n or "arac sarj" in n:
            runner.run("search_products", {"query": "araç şarj", "locale": "tr", "filters": {"in_stock_only": False}, "limit": 3})
            runner.run("search_products", {"query": "USB-C", "locale": "tr", "filters": {"in_stock_only": True}, "limit": 3})
            runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": "PRD-ACC-740", "quantity": 1, "idempotency_key": _add_key(message_id, "PRD-ACC-740"), "source_message_id": message_id})
            runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "stock_rule", "limit": 1})
            actions.append("Araç şarj adaptörü stok dışı olduğu için stoklu USB-C hızlı şarj alternatifi eklendi.")
        elif "offline" in n or "4g" in n or "senkron" in n:
            runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "compatibility", "limit": 1})
            if "4g" in n or "internet olmayacak" in n:
                runner.run("search_products", {"query": "4g el terminali", "locale": "tr", "filters": {"in_stock_only": True, "required_tags": ["4g"]}, "limit": 3})
                runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": "PRD-POS-210", "quantity": 1, "idempotency_key": _add_key(message_id, "PRD-POS-210"), "source_message_id": message_id})
            runner.run("search_products", {"query": "offline stok lisansı", "locale": "tr", "filters": {"in_stock_only": True, "required_tags": ["offline"]}, "limit": 3})
            runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": "PRD-SW-520", "quantity": 1, "idempotency_key": _add_key(message_id, "PRD-SW-520"), "source_message_id": message_id})
            if "şube" in n or "sube" in n:
                runner.run("search_products", {"query": "şube senkron", "locale": "tr", "filters": {"in_stock_only": True}, "limit": 3})
                runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": "PRD-SW-530", "quantity": 1, "idempotency_key": _add_key(message_id, "PRD-SW-530"), "source_message_id": message_id})
                runner.run("get_quote", {"quote_id": req.quote_id})
            actions.append("Uyumluluk kaynağına göre gerekli donanım/yazılım kalemleri teklife eklendi.")
        elif "ethernet" in n and ("çıkar" in n or "cikar" in n):
            runner.run("get_quote", {"quote_id": req.quote_id})
            runner.run("update_quote_item", {"quote_id": req.quote_id, "product_id": "PRD-PRN-320", "quantity": _quantity(req.message), "reason": "Kullanıcı miktar güncellemesi"})
            actions.append("Ethernet fiş yazıcısı miktarı güncellendi.")
        elif "yerinde kurulum" in n and ("güncelle" in n or "guncelle" in n or "lokasyon" in n):
            runner.run("get_quote", {"quote_id": req.quote_id})
            runner.run("update_quote_item", {"quote_id": req.quote_id, "product_id": "PRD-SVC-810", "quantity": _quantity(req.message), "reason": "Lokasyon sayısı güncellemesi"})
            runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "service_policy", "limit": 1})
            actions.append("Yerinde kurulum hizmeti miktarı lokasyon sayısına göre güncellendi.")
        elif "blueScan air plus".casefold() in n or "plus modelinden" in n or "plus toplam" in n:
            runner.run("get_quote", {"quote_id": req.quote_id})
            current = get_quote(db, req.quote_id).data
            existing = next((i for i in current["items"] if i["product_id"] == "PRD-BC-110-PLUS" and i["status"] == "active"), {"quantity": 0})
            target = 4 if "toplam 4" in n else existing["quantity"] + 1
            runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": "PRD-BC-110-PLUS", "quantity": max(target - existing["quantity"], 1), "idempotency_key": _add_key(message_id, "PRD-BC-110-PLUS"), "source_message_id": message_id})
            if "indirim" in n:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "discount_policy", "limit": 1})
                runner.run("get_quote", {"quote_id": req.quote_id})
            actions.append("BlueScan Air Plus miktarı tekrarsız şekilde güncellendi.")
        elif ("kablosuz" in n or "bluescan air" in n) and any(k in n for k in ["aynı", "ayni", "daha", "toplam"]):
            runner.run("get_quote", {"quote_id": req.quote_id})
            product_id = "PRD-BC-110"
            qty = _quantity(req.message)
            if "toplam" in n:
                current = get_quote(db, req.quote_id).data
                existing = next((i for i in current["items"] if i["product_id"] == product_id and i["status"] == "active"), {"quantity": 0})
                qty = max(qty - existing["quantity"], 0)
            runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": product_id, "quantity": qty, "idempotency_key": _add_key(message_id, product_id), "source_message_id": message_id})
            actions.append("Mevcut kablosuz okuyucu satırı ikinci aktif satır açmadan miktar olarak artırıldı.")
        elif "kablosuz" in n or "qr" in n or "bluescan air" in n:
            limit = _price_limit(req.message)
            qty = _quantity(req.message)
            search = runner.run("search_products", {"query": "BlueScan Air kablosuz QR barkod okuyucu", "locale": "tr", "filters": {"max_price_try": limit, "in_stock_only": True}, "limit": 5})
            candidates = [item for item in search.data if item["stock_qty"] > 0 and (limit is None or item["price_try"] <= limit)]
            product_id = "PRD-BC-110" if any(item["product_id"] == "PRD-BC-110" for item in candidates) else (candidates[0]["product_id"] if candidates else None)
            if not product_id:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "price_ceiling", "limit": 1})
                limit_text = f"{int(limit):,}".replace(",", ".") if limit is not None else "belirttiğiniz limit"
                actions.append(f"{limit_text} TL altında stokta kablosuz QR barkod okuyucu bulamadım.")
            else:
                runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": product_id, "quantity": qty, "idempotency_key": _add_key(message_id, product_id), "source_message_id": message_id, "max_price_try": limit})
                actions.append("Fiyat ve stok kısıtına uyan kablosuz okuyucu teklife eklendi; tekrar varsa aktif satır miktarı artırıldı.")
            if limit:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "price_ceiling", "limit": 1})
            if "indirim" in n or "partner" in n:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "discount_policy", "limit": 1})
            runner.run("get_quote", {"quote_id": req.quote_id})
        elif "koruyucu" in n or "kılıf" in n or "kilif" in n:
            limit = _price_limit(req.message)
            runner.run("search_products", {"query": "koruyucu kılıf", "locale": "tr", "filters": {"max_price_try": limit, "in_stock_only": True}, "limit": 5})
            runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": "PRD-ACC-710", "quantity": 1, "idempotency_key": _add_key(message_id, "PRD-ACC-710"), "source_message_id": message_id})
            runner.run("get_quote", {"quote_id": req.quote_id})
            actions.append("Fiyat limitinin altındaki stoklu koruyucu kılıf teklife eklendi.")
        else:
            if topic:
                limit = 2 if topic in {"return_policy", "delivery_policy"} else 1
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": topic, "limit": limit})
                if llm_unavailable and any(k in n for k in ["teklif", "hangi ürün", "hangi urun", "donanım", "donanim"]):
                    runner.run("get_quote", {"quote_id": req.quote_id})
                    runner.run("get_knowledge_entries", {"query": "fallback", "locale": "tr", "topic": "fallback", "limit": 1})
                    fallback_note = True
                actions.append("Kaynaklı politika cevabı üretildi; teklif üzerinde değişiklik yapılmadı.")
            else:
                runner.run("get_quote", {"quote_id": req.quote_id})
                if req.require_confirmation and not _has_business_signal(req.message):
                    actions.append("Bu konuda katalog veya teklif kaynağına dayalı bir bilgi bulamadım. Ürün, stok, fiyat, garanti, teslimat veya teklif isteğinizi yazabilirsiniz.")
                else:
                    actions.append("Teklif durumu kaynaklı olarak gösterildi.")

        for event in runner.events:
            yield event
        answer = _compose_text(actions, runner.sources, fallback_note)
        answer = _llm_rewrite(settings, req.message, answer, runner.sources)
        db.merge(ChatMessage(message_id=f"{message_id}-assistant", session_id=session_id, role="assistant", content=answer))
        db.commit()
        for chunk in re.findall(r".{1,80}(?:\s|$)", answer):
            yield sse("text_delta", {"text": chunk})
        yield sse("done", {"session_id": session_id, "message_id": message_id, "source_ids": list(dict.fromkeys(runner.sources))})
    except Exception as exc:
        yield sse("controlled_error", {"error": str(exc), "session_id": session_id, "message_id": message_id})
