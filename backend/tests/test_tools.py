from app.schemas import AddToQuoteRequest, ProductFilters, ReplaceWithAlternativeRequest, SearchProductsRequest, UpdateQuoteItemRequest
from app.tools import add_to_quote, get_quote, replace_with_alternative, search_products, update_quote_item


def test_price_limit_and_stock_filter_selects_basic_reader(db):
    result = search_products(
        db,
        SearchProductsRequest(
            query="kablosuz QR barkod okuyucu",
            filters=ProductFilters(max_price_try=8500, in_stock_only=True),
            limit=5,
        ),
    )
    ids = [item["product_id"] for item in result.data]
    assert "PRD-BC-110" in ids
    assert "PRD-BC-110-PLUS" not in ids
    assert "PRD-BC-120" not in ids


def test_add_to_quote_merges_active_line_and_idempotency(db):
    req = AddToQuoteRequest(
        quote_id="Q-1001",
        product_id="PRD-BC-110",
        quantity=2,
        idempotency_key="MSG-1:add:PRD-BC-110",
        source_message_id="MSG-1",
    )
    add_to_quote(db, req)
    replay = add_to_quote(db, req)
    quote = get_quote(db, "Q-1001").data
    rows = [i for i in quote["items"] if i["product_id"] == "PRD-BC-110" and i["status"] == "active"]
    assert len(rows) == 1
    assert rows[0]["quantity"] == 3
    assert replay.replayed is True


def test_out_of_stock_add_is_rejected_without_backorder_consent(db):
    req = AddToQuoteRequest(
        quote_id="Q-1001",
        product_id="PRD-BC-130",
        quantity=1,
        idempotency_key="MSG-2:add:PRD-BC-130",
        source_message_id="MSG-2",
    )
    try:
        add_to_quote(db, req)
    except ValueError as exc:
        assert "Stokta olmayan" in str(exc)
    else:
        raise AssertionError("out-of-stock product was added")


def test_update_quantity_zero_marks_inactive(db):
    update_quote_item(db, UpdateQuoteItemRequest(quote_id="Q-1003", product_id="PRD-PRN-320", quantity=0, reason="remove"))
    quote = get_quote(db, "Q-1003").data
    row = next(i for i in quote["items"] if i["product_id"] == "PRD-PRN-320")
    assert row["status"] == "inactive"
    assert quote["grand_total_try"] == 0


def test_replace_with_alternative_preserves_quantity(db):
    replace_with_alternative(
        db,
        ReplaceWithAlternativeRequest(
            quote_id="Q-1005",
            from_product_id="PRD-BC-130",
            to_product_id="PRD-BC-140",
            idempotency_key="MSG-3:replace:PRD-BC-130:PRD-BC-140",
        ),
    )
    quote = get_quote(db, "Q-1005").data
    old = next(i for i in quote["items"] if i["product_id"] == "PRD-BC-130")
    new = next(i for i in quote["items"] if i["product_id"] == "PRD-BC-140")
    assert old["status"] == "replaced"
    assert new["status"] == "active"
    assert new["quantity"] == 2

