from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Customer, IdempotencyKey, KnowledgeEntry, PriceRule, Product, Quote, QuoteItem
from .schemas import (
    AddToQuoteRequest,
    KnowledgeRequest,
    ReplaceWithAlternativeRequest,
    SearchProductsRequest,
    ToolResult,
    UpdateQuoteItemRequest,
)


def money(value) -> float:
    return float(value or 0)


def normalize(text: str) -> str:
    text = text.casefold().replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def product_payload(product: Product, evidence: list[str]) -> dict:
    return {
        "product_id": product.product_id,
        "sku": product.sku,
        "name_tr": product.name_tr,
        "price_try": money(product.price_try),
        "stock_qty": product.stock_qty,
        "category": product.category,
        "tags": product.tags,
        "match_evidence": evidence,
    }


def _product_evidence(product: Product, query: str, required_tags: list[str]) -> tuple[int, list[str]]:
    q = normalize(query)
    haystacks = [
        ("name_tr", product.name_tr),
        ("brand", product.brand),
        ("category", product.category),
        ("notes", product.notes),
        ("tags", " ".join(product.tags or [])),
        ("aliases.tr", " ".join((product.aliases or {}).get("tr", []))),
    ]
    score = 0
    evidence: list[str] = []
    terms = [t for t in re.split(r"\W+", q) if len(t) > 1]
    for field, value in haystacks:
        hv = normalize(value or "")
        if q and q in hv:
            score += 6
            evidence.append(f"{field}:phrase")
        for term in terms:
            if term in hv:
                score += 1
                if len(evidence) < 6:
                    evidence.append(f"{field}:{term}")
    for tag in required_tags:
        if normalize(tag) in [normalize(t) for t in product.tags or []]:
            score += 8
            evidence.append(f"tag:{tag}")
    if not query and required_tags:
        score += 1
    return score, list(dict.fromkeys(evidence))


def search_products(db: Session, req: SearchProductsRequest) -> ToolResult:
    products = db.scalars(select(Product).where(Product.active.is_(True))).all()
    matches: list[tuple[int, Product, list[str]]] = []
    for product in products:
        if req.filters.category and product.category != req.filters.category:
            continue
        if req.filters.max_price_try is not None and money(product.price_try) > req.filters.max_price_try:
            continue
        if req.filters.in_stock_only and product.stock_qty <= 0:
            continue
        if req.filters.required_tags:
            tags = {normalize(t) for t in product.tags or []}
            if not all(normalize(t) in tags for t in req.filters.required_tags):
                continue
        score, evidence = _product_evidence(product, req.query, req.filters.required_tags)
        if score > 0 or not req.query:
            if product.stock_qty <= 0:
                evidence.append("stock_qty:0 erişilemeyen eşleşme")
            matches.append((score, product, evidence or ["structured_filter"]))
    matches.sort(key=lambda x: (x[0], x[1].stock_qty > 0, -money(x[1].price_try)), reverse=True)
    data = [product_payload(p, ev) for _, p, ev in matches[: req.limit]]
    return ToolResult(data=data, source_ids=[p["product_id"] for p in data])


def get_knowledge_entries(db: Session, req: KnowledgeRequest) -> ToolResult:
    stmt = select(KnowledgeEntry).where(KnowledgeEntry.locale == req.locale)
    if req.topic:
        stmt = stmt.where(KnowledgeEntry.topic == req.topic)
    entries = db.scalars(stmt).all()
    q = normalize(req.query)
    ranked = []
    for entry in entries:
        text = normalize(" ".join([entry.topic, entry.title, entry.body, entry.source, " ".join(entry.applies_to or [])]))
        score = 10 if req.topic and entry.topic == req.topic else 0
        score += sum(1 for term in re.split(r"\W+", q) if term and term in text)
        ranked.append((score, entry))
    ranked.sort(key=lambda x: (x[1].topic == req.topic, not x[1].knowledge_id.endswith("-SUP"), x[0]), reverse=True)
    selected = [e for _, e in ranked[: req.limit]]
    data = [
        {
            "knowledge_id": e.knowledge_id,
            "topic": e.topic,
            "title": e.title,
            "body": e.body,
            "source": e.source,
            "applies_to": e.applies_to,
        }
        for e in selected
    ]
    return ToolResult(data=data, source_ids=[e["knowledge_id"] for e in data])


def _discount_for_item(item: QuoteItem, product: Product, quote: Quote, active_items: list[QuoteItem], db: Session) -> tuple[float, str | None]:
    customer = quote.customer
    qty_by_category = defaultdict(int)
    product_ids = set()
    for active in active_items:
        qty_by_category[active.product.category] += active.quantity
        product_ids.add(active.product_id)
    if product.category == "bundle":
        return 0, "RUL-BUNDLE-NO-STACK"
    if product.category == "service" and "acil" in (product.tags or []):
        return 0, "RUL-SVC-URGENT"
    if product.sku.endswith("PLUS") and item.quantity >= 4:
        return 6, "RUL-PLUS-QTY"
    if product.category == "software" and {"PRD-SW-520", "PRD-SW-530"}.issubset(product_ids):
        return 8, "RUL-SW-BUNDLE"
    if product.category == "accessory" and item.quantity >= 5:
        return 5, "RUL-ACC-5"
    if customer.price_tier == "partner" and product.category in {"barcode_scanner", "receipt_printer", "label_printer"} and qty_by_category[product.category] >= 3:
        return 7, "RUL-PARTNER-3"
    return 0, None


def get_quote(db: Session, quote_id: str) -> ToolResult:
    quote = db.get(Quote, quote_id)
    if not quote:
        raise ValueError(f"Teklif bulunamadı: {quote_id}")
    items = list(db.scalars(select(QuoteItem).where(QuoteItem.quote_id == quote.quote_id)).all())
    active_items = [i for i in items if i.status == "active"]
    lines = []
    subtotal = Decimal("0")
    discount_total = Decimal("0")
    source_ids: list[str] = []
    rule_ids: list[str] = []
    for item in items:
        product = item.product
        line_subtotal = Decimal(item.quantity) * Decimal(item.unit_price_try)
        discount_percent, rule_id = _discount_for_item(item, product, quote, active_items, db) if item.status == "active" else (0, None)
        discount_amount = line_subtotal * Decimal(str(discount_percent)) / Decimal("100")
        line_total = line_subtotal - discount_amount
        if item.status == "active":
            subtotal += line_subtotal
            discount_total += discount_amount
        if rule_id:
            rule_ids.append(rule_id)
        source_ids.append(product.product_id)
        lines.append(
            {
                "quote_item_id": item.quote_item_id,
                "product_id": product.product_id,
                "sku": product.sku,
                "name_tr": product.name_tr,
                "category": product.category,
                "quantity": item.quantity,
                "unit_price_try": money(item.unit_price_try),
                "status": item.status,
                "line_subtotal_try": money(line_subtotal),
                "discount_percent": discount_percent,
                "discount_rule_id": rule_id,
                "line_total_try": money(line_total),
                "replaced_by_product_id": item.replaced_by_product_id,
            }
        )
    data = {
        "quote_id": quote.quote_id,
        "customer_id": quote.customer_id,
        "customer_name": quote.customer.name,
        "status": quote.status,
        "currency": quote.currency,
        "items": lines,
        "discounts": sorted(set(rule_ids)),
        "subtotal_try": money(subtotal),
        "discount_total_try": money(discount_total),
        "grand_total_try": money(subtotal - discount_total),
    }
    return ToolResult(data=data, source_ids=source_ids + sorted(set(rule_ids)))


def _ensure_add_allowed(db: Session, quote: Quote, product: Product, allow_wait: bool) -> None:
    if product.stock_qty <= 0 and not (allow_wait and quote.customer.allow_backorder):
        raise ValueError("Stokta olmayan ürün, açık bekleme onayı ve müşteri backorder uygunluğu olmadan eklenemez.")


def add_to_quote(db: Session, req: AddToQuoteRequest) -> ToolResult:
    existing_key = db.get(IdempotencyKey, req.idempotency_key)
    if existing_key:
        data = dict(existing_key.result_json)
        data["replayed"] = True
        return ToolResult(data=data, source_ids=[req.product_id, "KNE-IDEMP-001"], quote_delta={}, replayed=True)

    quote = db.get(Quote, req.quote_id)
    product = db.get(Product, req.product_id)
    if not quote or not product:
        raise ValueError("Teklif veya ürün bulunamadı.")
    _ensure_add_allowed(db, quote, product, req.allow_wait)
    active = db.scalar(
        select(QuoteItem).where(
            QuoteItem.quote_id == quote.quote_id,
            QuoteItem.product_id == product.product_id,
            QuoteItem.status == "active",
        )
    )
    before_qty = active.quantity if active else 0
    if active:
        active.quantity += req.quantity
        active.source_message_id = req.source_message_id
    else:
        active = QuoteItem(
            quote_item_id=f"QI-{uuid4().hex[:12]}",
            quote_id=quote.quote_id,
            product_id=product.product_id,
            quantity=req.quantity,
            unit_price_try=product.price_try,
            status="active",
            source_message_id=req.source_message_id,
            idempotency_key=req.idempotency_key,
        )
        db.add(active)
    delta = {"product_id": product.product_id, "before_quantity": before_qty, "after_quantity": before_qty + req.quantity}
    result = {"quote_id": quote.quote_id, "product_id": product.product_id, "quantity": req.quantity, "quote_delta": delta}
    db.add(IdempotencyKey(key=req.idempotency_key, tool_name="add_to_quote", quote_id=quote.quote_id, result_json=result))
    db.commit()
    source_ids = [product.product_id]
    if before_qty > 0:
        source_ids.append("KNE-IDEMP-001")
    return ToolResult(data=result, source_ids=source_ids, quote_delta=delta)


def update_quote_item(db: Session, req: UpdateQuoteItemRequest) -> ToolResult:
    quote = db.get(Quote, req.quote_id)
    if not quote:
        raise ValueError("Teklif bulunamadı.")
    item = db.scalar(
        select(QuoteItem).where(
            QuoteItem.quote_id == req.quote_id,
            QuoteItem.product_id == req.product_id,
            QuoteItem.status == "active",
        )
    )
    if not item:
        raise ValueError("Aktif teklif kalemi bulunamadı.")
    before_qty = item.quantity
    item.quantity = max(req.quantity, 0)
    if req.quantity == 0:
        item.status = "inactive"
    db.commit()
    delta = {"product_id": req.product_id, "before_quantity": before_qty, "after_quantity": req.quantity, "status": item.status}
    return ToolResult(data={"quote_id": req.quote_id, "product_id": req.product_id, "quantity": req.quantity}, source_ids=[req.product_id], quote_delta=delta)


def replace_with_alternative(db: Session, req: ReplaceWithAlternativeRequest) -> ToolResult:
    existing_key = db.get(IdempotencyKey, req.idempotency_key)
    if existing_key:
        data = dict(existing_key.result_json)
        data["replayed"] = True
        return ToolResult(data=data, source_ids=[req.from_product_id, req.to_product_id], replayed=True)
    quote = db.get(Quote, req.quote_id)
    from_product = db.get(Product, req.from_product_id)
    to_product = db.get(Product, req.to_product_id)
    if not quote or not from_product or not to_product:
        raise ValueError("Teklif veya ürün bulunamadı.")
    if to_product.stock_qty <= 0:
        raise ValueError("Alternatif ürün stokta değil.")
    if req.max_price_try is not None and money(to_product.price_try) > req.max_price_try:
        raise ValueError("Alternatif ürün fiyat limitini aşıyor.")
    old = db.scalar(
        select(QuoteItem).where(
            QuoteItem.quote_id == quote.quote_id,
            QuoteItem.product_id == from_product.product_id,
            QuoteItem.status == "active",
        )
    )
    if not old:
        raise ValueError("Değiştirilecek aktif kalem bulunamadı.")
    qty = req.quantity or old.quantity
    old.status = "replaced"
    old.replaced_by_product_id = to_product.product_id
    existing_target = db.scalar(
        select(QuoteItem).where(
            QuoteItem.quote_id == quote.quote_id,
            QuoteItem.product_id == to_product.product_id,
            QuoteItem.status == "active",
        )
    )
    if existing_target:
        existing_target.quantity += qty
    else:
        db.add(
            QuoteItem(
                quote_item_id=f"QI-{uuid4().hex[:12]}",
                quote_id=quote.quote_id,
                product_id=to_product.product_id,
                quantity=qty,
                unit_price_try=to_product.price_try,
                status="active",
                source_message_id=req.idempotency_key,
                idempotency_key=req.idempotency_key,
            )
        )
    delta = {"from_product_id": from_product.product_id, "to_product_id": to_product.product_id, "quantity": qty}
    result = {"quote_id": quote.quote_id, **delta}
    db.add(IdempotencyKey(key=req.idempotency_key, tool_name="replace_with_alternative", quote_id=quote.quote_id, result_json=result))
    db.commit()
    return ToolResult(data=result, source_ids=[from_product.product_id, to_product.product_id], quote_delta=delta)
