from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .models import Customer, KnowledgeEntry, Product, Quote, ToolCallLog
from .orchestrator import plan_and_execute
from .schemas import ChatStreamRequest, CustomerCreateRequest, QuoteCreateRequest, UpdateQuoteItemRequest
from .seed import seed_database
from .tools import get_quote, update_quote_item

app = FastAPI(title="The Blue Red AI Quote Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    if get_settings().auto_seed:
        from .database import SessionLocal

        db = SessionLocal()
        try:
            seed_database(db, get_settings().dataset_dir)
        finally:
            db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/products")
def list_products(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_product_dict(p) for p in db.scalars(select(Product).order_by(Product.product_id)).all()]


@app.post("/products")
def create_product(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    product = Product(**payload)
    db.add(product)
    db.commit()
    return _product_dict(product)


@app.put("/products/{product_id}")
def update_product(product_id: str, payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    product = db.get(Product, product_id)
    if not product:
        payload["product_id"] = product_id
        product = Product(**payload)
        db.add(product)
    else:
        for key, value in payload.items():
            setattr(product, key, value)
    db.commit()
    return _product_dict(product)


@app.get("/knowledge")
def list_knowledge(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_knowledge_dict(k) for k in db.scalars(select(KnowledgeEntry).order_by(KnowledgeEntry.knowledge_id)).all()]


@app.post("/knowledge")
def create_knowledge(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    entry = KnowledgeEntry(**payload)
    db.add(entry)
    db.commit()
    return _knowledge_dict(entry)


@app.put("/knowledge/{knowledge_id}")
def update_knowledge(knowledge_id: str, payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    entry = db.get(KnowledgeEntry, knowledge_id)
    if not entry:
        payload["knowledge_id"] = knowledge_id
        entry = KnowledgeEntry(**payload)
        db.add(entry)
    else:
        for key, value in payload.items():
            setattr(entry, key, value)
    db.commit()
    return _knowledge_dict(entry)


@app.get("/customers")
def list_customers(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_customer_dict(c) for c in db.scalars(select(Customer).order_by(Customer.customer_id)).all()]


@app.get("/customers/{customer_id}")
def read_customer(customer_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
    return _customer_dict(customer)


@app.post("/customers")
def create_customer(payload: CustomerCreateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    customer = Customer(
        customer_id=_next_customer_id(db),
        name=payload.name,
        segment="new",
        city=payload.city,
        price_tier=payload.price_tier,
        credit_limit_try=0,
        allow_backorder=payload.allow_backorder,
        default_locale="tr",
        notes="",
    )
    db.add(customer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Müşteri ID çakıştı, tekrar deneyin.") from exc
    return _customer_dict(customer)


@app.get("/customers/{customer_id}/quotes")
def list_customer_quotes(customer_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    if not db.get(Customer, customer_id):
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
    stmt = select(Quote).where(Quote.customer_id == customer_id).order_by(Quote.quote_id)
    return [_quote_summary(q) for q in db.scalars(stmt).all()]


@app.post("/quotes")
def create_quote(payload: QuoteCreateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not db.get(Customer, payload.customer_id):
        raise HTTPException(status_code=400, detail="Müşteri bulunamadı.")
    quote = Quote(
        quote_id=_next_quote_id(db),
        customer_id=payload.customer_id,
        status="draft",
        created_by_channel=payload.created_by_channel,
        currency=payload.currency,
        notes=payload.notes,
    )
    db.add(quote)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Teklif ID çakıştı, tekrar deneyin.") from exc
    return get_quote(db, quote.quote_id).data


@app.get("/quotes/{quote_id}")
def read_quote(quote_id: str, db: Session = Depends(get_db)) -> dict:
    return get_quote(db, quote_id).data


@app.post("/quotes/{quote_id}/items/{product_id}/quantity")
def set_quote_item_quantity(quote_id: str, product_id: str, payload: dict[str, Any], db: Session = Depends(get_db)) -> dict:
    quote = db.get(Quote, quote_id)
    customer_id = payload.get("customer_id")
    if customer_id and quote and quote.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="Teklif bu müşteriye ait değil.")
    result = update_quote_item(
        db,
        UpdateQuoteItemRequest(
            quote_id=quote_id,
            product_id=product_id,
            quantity=int(payload.get("quantity", 0)),
            reason=payload.get("reason", "manual quantity control"),
        ),
    )
    return {"result": result.data, "quote": get_quote(db, quote_id).data}


@app.get("/tool-call-logs")
def tool_call_logs(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_log_dict(log) for log in db.scalars(select(ToolCallLog).order_by(ToolCallLog.id.desc())).all()]


@app.get("/sessions/{session_id}/tool-calls")
def session_tool_calls(session_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    stmt = select(ToolCallLog).where(ToolCallLog.session_id == session_id).order_by(ToolCallLog.sequence_no)
    return [_log_dict(log) for log in db.scalars(stmt).all()]


@app.post("/chat/stream")
def chat_stream(req: ChatStreamRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    return StreamingResponse(plan_and_execute(db, req), media_type="text/event-stream")


@app.get("/chat/stream")
def chat_stream_get(
    quote_id: str,
    message: str,
    customer_id: str | None = None,
    channel: str = "web",
    session_id: str | None = None,
    message_id: str | None = None,
    require_confirmation: bool = True,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    req = ChatStreamRequest(quote_id=quote_id, customer_id=customer_id, channel=channel, session_id=session_id, message_id=message_id, message=message, require_confirmation=require_confirmation)
    return StreamingResponse(plan_and_execute(db, req), media_type="text/event-stream")


@app.post("/seed/reset")
def reset_seed(db: Session = Depends(get_db)) -> dict[str, str]:
    seed_database(db, get_settings().dataset_dir, force=True)
    return {"status": "seeded"}


def _product_dict(p: Product) -> dict[str, Any]:
    return {
        "product_id": p.product_id,
        "sku": p.sku,
        "name_tr": p.name_tr,
        "category": p.category,
        "brand": p.brand,
        "price_try": float(p.price_try),
        "stock_qty": p.stock_qty,
        "active": p.active,
        "tags": p.tags,
        "aliases": p.aliases,
        "substitute_product_ids": p.substitute_product_ids,
        "notes": p.notes,
    }


def _knowledge_dict(k: KnowledgeEntry) -> dict[str, Any]:
    return {
        "knowledge_id": k.knowledge_id,
        "topic": k.topic,
        "locale": k.locale,
        "title": k.title,
        "body": k.body,
        "source": k.source,
        "applies_to": k.applies_to,
        "effective_from": str(k.effective_from),
    }


def _customer_dict(c: Customer) -> dict[str, Any]:
    return {
        "customer_id": c.customer_id,
        "name": c.name,
        "company_name": c.name,
        "city": c.city,
        "location": c.city,
        "segment": c.segment,
        "price_tier": c.price_tier,
        "allow_backorder": c.allow_backorder,
        "default_locale": c.default_locale,
        "notes": c.notes,
    }


def _quote_summary(q: Quote) -> dict[str, Any]:
    return {
        "quote_id": q.quote_id,
        "customer_id": q.customer_id,
        "status": q.status,
        "created_by_channel": q.created_by_channel,
        "currency": q.currency,
        "notes": q.notes,
    }


def _next_customer_id(db: Session) -> str:
    existing = set(db.scalars(select(Customer.customer_id)).all())
    for idx in range(1, 10000):
        candidate = f"CUST-NEW-{idx:03d}"
        if candidate not in existing:
            return candidate
    raise ValueError("Yeni müşteri ID üretilemedi.")


def _next_quote_id(db: Session) -> str:
    existing = set(db.scalars(select(Quote.quote_id)).all())
    for idx in range(1, 10000):
        candidate = f"Q-NEW-{idx:03d}"
        if candidate not in existing:
            return candidate
    raise ValueError("Yeni teklif ID üretilemedi.")


def _log_dict(log: ToolCallLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "session_id": log.session_id,
        "message_id": log.message_id,
        "sequence_no": log.sequence_no,
        "tool_name": log.tool_name,
        "input_json": log.input_json,
        "output_json": log.output_json,
        "success": log.success,
        "error": log.error,
        "source_ids": log.source_ids,
        "quote_id": log.quote_id,
        "quote_delta": log.quote_delta,
        "created_at": log.created_at.isoformat(),
    }
