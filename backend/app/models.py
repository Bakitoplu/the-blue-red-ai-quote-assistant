from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


class Product(Base):
    __tablename__ = "products"
    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    name_tr: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    brand: Mapped[str] = mapped_column(String, nullable=False)
    price_try: Mapped[float] = mapped_column(Numeric, nullable=False)
    stock_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_order_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warranty_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    aliases: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    substitute_product_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    knowledge_id: Mapped[str] = mapped_column(String, primary_key=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[str] = mapped_column(String, nullable=False, default="tr")
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    applies_to: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    effective_from: Mapped[str] = mapped_column(Date, nullable=False)


class Customer(Base):
    __tablename__ = "customers"
    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    segment: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    price_tier: Mapped[str] = mapped_column(String, nullable=False)
    credit_limit_try: Mapped[float] = mapped_column(Numeric, nullable=False)
    allow_backorder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_locale: Mapped[str] = mapped_column(String, nullable=False, default="tr")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class PriceRule(Base):
    __tablename__ = "price_rules"
    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric, nullable=False)


class Quote(Base):
    __tablename__ = "quotes"
    quote_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_by_channel: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="TRY")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    customer: Mapped[Customer] = relationship()
    items: Mapped[list["QuoteItem"]] = relationship(back_populates="quote")


class QuoteItem(Base):
    __tablename__ = "quote_items"
    quote_item_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"QI-{uuid4().hex[:12]}")
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.quote_id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_try: Mapped[float] = mapped_column(Numeric, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    source_message_id: Mapped[str] = mapped_column(String, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    replaced_by_product_id: Mapped[str | None] = mapped_column(String, nullable=True)
    quote: Mapped[Quote] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    quote_id: Mapped[str] = mapped_column(String, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ToolCallLog(Base):
    __tablename__ = "tool_call_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    message_id: Mapped[str] = mapped_column(String, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    quote_id: Mapped[str | None] = mapped_column(String, nullable=True)
    quote_delta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("message_id", "sequence_no", name="uq_tool_call_message_seq"),)


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    quote_id: Mapped[str] = mapped_column(String, nullable=False)
    customer_id: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
