from app.config import get_settings
from app.models import ToolCallLog
from app.orchestrator import plan_and_execute
from app.schemas import ChatStreamRequest
from app.tools import get_quote


def drain(db, req):
    return "".join(plan_and_execute(db, req))


def tool_names(db, message_id):
    return [log.tool_name for log in db.query(ToolCallLog).filter(ToolCallLog.message_id == message_id).order_by(ToolCallLog.sequence_no).all()]


def test_golden_wireless_add_under_limit(db):
    drain(
        db,
        ChatStreamRequest(
            quote_id="Q-1002",
            customer_id="CUST-ANK-002",
            channel="mobile",
            session_id="S1",
            message_id="SCN-001",
            message="9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?",
        ),
    )
    assert tool_names(db, "SCN-001")[:2] == ["search_products", "add_to_quote"]
    quote = get_quote(db, "Q-1002").data
    row = next(i for i in quote["items"] if i["product_id"] == "PRD-BC-110" and i["status"] == "active")
    assert row["quantity"] == 1


def test_golden_policy_is_mutation_free(db):
    before = get_quote(db, "Q-1001").data["grand_total_try"]
    drain(
        db,
        ChatStreamRequest(
            quote_id="Q-1001",
            customer_id="CUST-IST-001",
            channel="mobile",
            session_id="S7",
            message_id="SCN-007",
            message="Aktive edilmiş yazılım lisansını iade edebilir miyiz?",
        ),
    )
    assert tool_names(db, "SCN-007") == ["get_knowledge_entries"]
    assert get_quote(db, "Q-1001").data["grand_total_try"] == before


def test_golden_fallback_does_not_mutate(db):
    get_settings().openai_api_key = ""
    before_qty = next(i for i in get_quote(db, "Q-1001").data["items"] if i["product_id"] == "PRD-BC-110")["quantity"]
    events = drain(
        db,
        ChatStreamRequest(
            quote_id="Q-1001",
            customer_id="CUST-IST-001",
            channel="web",
            session_id="S9",
            message_id="SCN-009",
            message="İade süresi nedir ve teklifimde hangi ürün var?",
        ),
    )
    assert "KNE-FALL-001" in events or "Yedek modda" in events
    assert tool_names(db, "SCN-009") == ["get_knowledge_entries", "get_quote"]
    after_qty = next(i for i in get_quote(db, "Q-1001").data["items"] if i["product_id"] == "PRD-BC-110")["quantity"]
    assert after_qty == before_qty


def test_repeat_same_message_id_increments_once(db):
    req = ChatStreamRequest(
        quote_id="Q-1001",
        customer_id="CUST-IST-001",
        channel="mobile",
        session_id="S10",
        message_id="SCN-010",
        message="Kablosuz barkod okuyucudan 1 tane daha ekle.",
    )
    drain(db, req)
    drain(db, req)
    row = next(i for i in get_quote(db, "Q-1001").data["items"] if i["product_id"] == "PRD-BC-110" and i["status"] == "active")
    assert row["quantity"] == 2
