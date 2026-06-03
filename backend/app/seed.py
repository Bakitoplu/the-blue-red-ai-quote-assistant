import json
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import Customer, KnowledgeEntry, PriceRule, Product, Quote, QuoteItem


MODEL_BY_FILE = {
    "products": Product,
    "knowledge_entries": KnowledgeEntry,
    "customers": Customer,
    "price_rules": PriceRule,
    "quotes": Quote,
    "quote_items": QuoteItem,
}


def _rows(dataset_dir: Path, name: str) -> list[dict]:
    return json.loads((dataset_dir / f"{name}.json").read_text(encoding="utf-8"))


def seed_database(db: Session, dataset_dir: Path, force: bool = False) -> None:
    has_products = db.scalar(select(Product.product_id).limit(1))
    if has_products and not force:
        return

    for model in [QuoteItem, Quote, PriceRule, Customer, KnowledgeEntry, Product]:
        db.execute(delete(model))

    for name in ["products", "knowledge_entries", "customers", "price_rules", "quotes", "quote_items"]:
        model = MODEL_BY_FILE[name]
        for row in _rows(dataset_dir, name):
            if name == "knowledge_entries":
                row["effective_from"] = date.fromisoformat(row["effective_from"])
            db.merge(model(**row))
    db.commit()

