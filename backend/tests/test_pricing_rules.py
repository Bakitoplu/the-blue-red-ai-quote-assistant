from app.schemas import AddToQuoteRequest
from app.tools import add_to_quote, get_quote


def add(db, quote_id, product_id, quantity):
    add_to_quote(
        db,
        AddToQuoteRequest(
            quote_id=quote_id,
            product_id=product_id,
            quantity=quantity,
            idempotency_key=f"test:{quote_id}:{product_id}:{quantity}",
            source_message_id="pricing-test",
        ),
    )


def line(quote, product_id):
    return next(item for item in quote["items"] if item["product_id"] == product_id and item["status"] == "active")


def test_partner_category_quantity_discount(db):
    add(db, "Q-1002", "PRD-BC-110", 3)
    quote = get_quote(db, "Q-1002").data
    assert line(quote, "PRD-BC-110")["discount_rule_id"] == "RUL-PARTNER-3"
    assert line(quote, "PRD-BC-110")["discount_percent"] == 7


def test_accessory_quantity_discount(db):
    add(db, "Q-1002", "PRD-ACC-710", 5)
    quote = get_quote(db, "Q-1002").data
    assert line(quote, "PRD-ACC-710")["discount_rule_id"] == "RUL-ACC-5"
    assert line(quote, "PRD-ACC-710")["discount_percent"] == 5


def test_bundle_no_extra_discount(db):
    add(db, "Q-1002", "PRD-KIT-610", 1)
    quote = get_quote(db, "Q-1002").data
    assert line(quote, "PRD-KIT-610")["discount_rule_id"] == "RUL-BUNDLE-NO-STACK"
    assert line(quote, "PRD-KIT-610")["discount_percent"] == 0


def test_urgent_service_no_discount(db):
    add(db, "Q-1002", "PRD-SVC-820", 1)
    quote = get_quote(db, "Q-1002").data
    assert line(quote, "PRD-SVC-820")["discount_rule_id"] == "RUL-SVC-URGENT"
    assert line(quote, "PRD-SVC-820")["discount_percent"] == 0


def test_software_bundle_discount(db):
    add(db, "Q-1002", "PRD-SW-520", 1)
    add(db, "Q-1002", "PRD-SW-530", 1)
    quote = get_quote(db, "Q-1002").data
    assert line(quote, "PRD-SW-520")["discount_rule_id"] == "RUL-SW-BUNDLE"
    assert line(quote, "PRD-SW-530")["discount_rule_id"] == "RUL-SW-BUNDLE"
    assert line(quote, "PRD-SW-520")["discount_percent"] == 8


def test_plus_volume_discount(db):
    add(db, "Q-1002", "PRD-BC-110-PLUS", 4)
    quote = get_quote(db, "Q-1002").data
    assert line(quote, "PRD-BC-110-PLUS")["discount_rule_id"] == "RUL-PLUS-QTY"
    assert line(quote, "PRD-BC-110-PLUS")["discount_percent"] == 6
