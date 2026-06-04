from typing import Any

from pydantic import BaseModel, Field


class ProductFilters(BaseModel):
    category: str | None = None
    max_price_try: float | None = None
    in_stock_only: bool = False
    required_tags: list[str] = Field(default_factory=list)


class SearchProductsRequest(BaseModel):
    query: str = ""
    locale: str = "tr"
    filters: ProductFilters = Field(default_factory=ProductFilters)
    limit: int = 5


class KnowledgeRequest(BaseModel):
    query: str = ""
    locale: str = "tr"
    topic: str | None = None
    limit: int = 3


class AddToQuoteRequest(BaseModel):
    quote_id: str
    product_id: str
    quantity: int
    idempotency_key: str
    source_message_id: str
    allow_wait: bool = False
    max_price_try: float | None = None


class UpdateQuoteItemRequest(BaseModel):
    quote_id: str
    product_id: str
    quantity: int
    reason: str = ""


class ReplaceWithAlternativeRequest(BaseModel):
    quote_id: str
    from_product_id: str
    to_product_id: str
    quantity: int | None = None
    reason: str = ""
    idempotency_key: str
    max_price_try: float | None = None


class ChatStreamRequest(BaseModel):
    quote_id: str
    customer_id: str | None = None
    channel: str = "web"
    session_id: str | None = None
    message_id: str | None = None
    message: str
    require_confirmation: bool = True
    mode: str = "user"


class CustomerCreateRequest(BaseModel):
    name: str
    city: str = ""
    price_tier: str = "standard"
    allow_backorder: bool = False


class QuoteCreateRequest(BaseModel):
    customer_id: str
    created_by_channel: str = "web"
    notes: str = ""


class ToolResult(BaseModel):
    data: Any
    source_ids: list[str] = Field(default_factory=list)
    quote_delta: dict = Field(default_factory=dict)
    replayed: bool = False
