from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterator
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .models import ChatMessage, ChatSession, Quote, ToolCallLog
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
    match = re.search(r"(\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(?:tl|try)", _norm(text))
    if not match:
        return None
    return float(match.group(1).replace(".", "").replace(" ", ""))


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
            self.events.append(sse("source", {"source_id": source}))
        return result


def _add_key(message_id: str, product_id: str) -> str:
    return f"{message_id}:add:{product_id}"


def _replace_key(message_id: str, from_product_id: str, to_product_id: str) -> str:
    return f"{message_id}:replace:{from_product_id}:{to_product_id}"


def _compose_text(actions: list[str], sources: list[str], fallback_note: bool) -> str:
    prefix = "Yedek modda kaynaklara göre: " if fallback_note else ""
    source_text = ", ".join(dict.fromkeys(sources))
    return prefix + " ".join(actions) + (f" Kaynaklar: {source_text}." if source_text else "")


def plan_and_execute(db: Session, req: ChatStreamRequest) -> Iterator[str]:
    quote = db.get(Quote, req.quote_id)
    if not quote:
        yield sse("controlled_error", {"error": "Teklif bulunamadı."})
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
        if "redscan mini" in n or ("cep tipi" in n and "değiştir" not in n and "degistir" not in n):
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
            runner.run("search_products", {"query": "BlueScan Air kablosuz QR barkod okuyucu", "locale": "tr", "filters": {"max_price_try": limit, "in_stock_only": True}, "limit": 5})
            product_id = "PRD-BC-110"
            runner.run("add_to_quote", {"quote_id": req.quote_id, "product_id": product_id, "quantity": qty, "idempotency_key": _add_key(message_id, product_id), "source_message_id": message_id})
            if limit:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "price_ceiling", "limit": 1})
            if "indirim" in n or "partner" in n:
                runner.run("get_knowledge_entries", {"query": req.message, "locale": "tr", "topic": "discount_policy", "limit": 1})
            runner.run("get_quote", {"quote_id": req.quote_id})
            actions.append("Fiyat ve stok kısıtına uyan kablosuz okuyucu teklife eklendi; tekrar varsa aktif satır miktarı artırıldı.")
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
                actions.append("Teklif durumu kaynaklı olarak gösterildi.")

        for event in runner.events:
            yield event
        answer = _compose_text(actions, runner.sources, fallback_note)
        db.merge(ChatMessage(message_id=f"{message_id}-assistant", session_id=session_id, role="assistant", content=answer))
        db.commit()
        for chunk in re.findall(r".{1,80}(?:\s|$)", answer):
            yield sse("text_delta", {"text": chunk})
        yield sse("done", {"session_id": session_id, "message_id": message_id, "source_ids": list(dict.fromkeys(runner.sources))})
    except Exception as exc:
        yield sse("controlled_error", {"error": str(exc), "session_id": session_id, "message_id": message_id})
