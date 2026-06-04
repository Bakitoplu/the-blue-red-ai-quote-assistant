from app.models import PendingAction, ToolCallLog
from app.orchestrator import plan_and_execute
from app.schemas import AddToQuoteRequest, ChatStreamRequest
from app.tools import add_to_quote, get_quote


def drain(db, req):
    return "".join(plan_and_execute(db, req))


def names(db, message_id):
    return [log.tool_name for log in db.query(ToolCallLog).filter(ToolCallLog.message_id == message_id).order_by(ToolCallLog.sequence_no)]


def qty(db, quote_id, product_id):
    rows = [item for item in get_quote(db, quote_id).data["items"] if item["product_id"] == product_id and item["status"] == "active"]
    return rows[0]["quantity"] if rows else 0


def test_product_price_and_stock_question_is_mutation_free(db):
    before = get_quote(db, "Q-1001").data
    events = drain(db, ChatStreamRequest(quote_id="Q-1001", customer_id="CUST-IST-001", session_id="QA1", message_id="QA1-M", message="BlueScan Air fiyatı ne kadar ve stokta var mı?"))
    assert names(db, "QA1-M") == ["search_products"]
    assert "7990" in events or "7990.0" in events
    assert "18" in events
    assert get_quote(db, "Q-1001").data == before


def test_product_qr_question_is_mutation_free(db):
    before = get_quote(db, "Q-1001").data
    events = drain(db, ChatStreamRequest(quote_id="Q-1001", customer_id="CUST-IST-001", session_id="QA2", message_id="QA2-M", message="BlueScan Air QR destekli mi?"))
    assert "QR/2D desteği var" in events
    assert "add_to_quote" not in names(db, "QA2-M")
    assert get_quote(db, "Q-1001").data == before


def test_product_warranty_question_uses_catalog_and_policy(db):
    events = drain(db, ChatStreamRequest(quote_id="Q-1001", customer_id="CUST-IST-001", session_id="QA3", message_id="QA3-M", message="PRD-BC-110 ürününün garantisi kaç ay?"))
    assert names(db, "QA3-M") == ["search_products", "get_knowledge_entries"]
    assert "24 ay" in events
    assert "KNE-WAR-001" in events


def test_out_of_stock_product_question_is_mutation_free(db):
    events = drain(db, ChatStreamRequest(quote_id="Q-1001", customer_id="CUST-IST-001", session_id="QA4", message_id="QA4-M", message="RedScan Mini stokta var mı?"))
    assert "stok 0 adet" in events
    assert "KNE-STOCK-001" in events
    assert "add_to_quote" not in names(db, "QA4-M")
    assert qty(db, "Q-1001", "PRD-BC-130") == 0


def test_price_limit_blocks_unsafe_add_in_contract_mode(db):
    before = qty(db, "Q-1002", "PRD-BC-110")
    events = drain(
        db,
        ChatStreamRequest(
            quote_id="Q-1002",
            customer_id="CUST-ANK-002",
            session_id="P1",
            message_id="P1-M",
            message="1.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?",
            require_confirmation=False,
        ),
    )
    assert "add_to_quote" not in names(db, "P1-M")
    assert qty(db, "Q-1002", "PRD-BC-110") == before
    assert "KNE-PRICE-001" in events


def test_user_mode_creates_pending_action_then_applies_on_confirmation(db):
    first = drain(db, ChatStreamRequest(quote_id="Q-1002", customer_id="CUST-ANK-002", session_id="CONF1", message_id="CONF1-A", message="9.000 TL altında stokta kablosuz QR okuyucu ekler misin?"))
    assert "add_to_quote" not in names(db, "CONF1-A")
    assert db.query(PendingAction).filter_by(session_id="CONF1", status="pending").one().product_id == "PRD-BC-110"
    assert "eklememi ister misiniz" in first
    assert qty(db, "Q-1002", "PRD-BC-110") == 0
    second = drain(db, ChatStreamRequest(quote_id="Q-1002", customer_id="CUST-ANK-002", session_id="CONF1", message_id="CONF1-B", message="evet ekle"))
    assert "add_to_quote" in names(db, "CONF1-B")
    assert qty(db, "Q-1002", "PRD-BC-110") == 1


def test_user_mode_add_request_with_product_question_words_still_requires_confirmation(db):
    events = drain(
        db,
        ChatStreamRequest(
            quote_id="Q-1002",
            customer_id="CUST-ANK-002",
            session_id="CONF1B",
            message_id="CONF1B-A",
            message="9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?",
        ),
    )
    assert names(db, "CONF1B-A") == ["search_products"]
    assert "add_to_quote" not in names(db, "CONF1B-A")
    assert db.query(PendingAction).filter_by(session_id="CONF1B", status="pending").one().product_id == "PRD-BC-110"
    assert "eklememi ister misiniz" in events


def test_user_mode_cancels_pending_action(db):
    drain(db, ChatStreamRequest(quote_id="Q-1002", customer_id="CUST-ANK-002", session_id="CONF2", message_id="CONF2-A", message="9.000 TL altında stokta kablosuz QR okuyucu ekler misin?"))
    drain(db, ChatStreamRequest(quote_id="Q-1002", customer_id="CUST-ANK-002", session_id="CONF2", message_id="CONF2-B", message="iptal"))
    assert qty(db, "Q-1002", "PRD-BC-110") == 0
    assert db.query(PendingAction).filter_by(session_id="CONF2").one().status == "cancelled"


def test_backorder_rules(db):
    try:
        add_to_quote(db, AddToQuoteRequest(quote_id="Q-1001", product_id="PRD-BC-130", quantity=1, idempotency_key="bo-1", source_message_id="bo"))
    except ValueError:
        pass
    else:
        raise AssertionError("standard customer added out-of-stock product")

    result = add_to_quote(db, AddToQuoteRequest(quote_id="Q-1002", product_id="PRD-BC-130", quantity=1, idempotency_key="bo-2", source_message_id="bo", allow_wait=True))
    row = next(item for item in get_quote(db, "Q-1002").data["items"] if item["product_id"] == "PRD-BC-130")
    assert row["status"] == "backorder"

    try:
        add_to_quote(db, AddToQuoteRequest(quote_id="Q-1001", product_id="PRD-BC-130", quantity=1, idempotency_key="bo-3", source_message_id="bo", allow_wait=True))
    except ValueError:
        pass
    else:
        raise AssertionError("non-backorder customer added out-of-stock product")
