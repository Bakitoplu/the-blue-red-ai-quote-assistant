from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .models import KnowledgeEntry, Product, ToolCallLog
from .orchestrator import plan_and_execute
from .schemas import ChatStreamRequest
from .seed import seed_database
from .tools import get_quote

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


@app.get("/quotes/{quote_id}")
def read_quote(quote_id: str, db: Session = Depends(get_db)) -> dict:
    return get_quote(db, quote_id).data


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
    db: Session = Depends(get_db),
) -> StreamingResponse:
    req = ChatStreamRequest(quote_id=quote_id, customer_id=customer_id, channel=channel, session_id=session_id, message_id=message_id, message=message)
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

