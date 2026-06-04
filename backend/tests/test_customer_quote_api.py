from fastapi.testclient import TestClient
import re

from app.database import get_db
from app.main import app
from app.orchestrator import plan_and_execute
from app.schemas import ChatStreamRequest
from app.tools import get_quote


def client_for(db):
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_customers_list_and_create_customer(db):
    client = client_for(db)
    try:
        listed = client.get("/customers")
        assert listed.status_code == 200
        assert any(item["customer_id"] == "CUST-ANK-002" for item in listed.json())

        created = client.post(
            "/customers",
            json={"name": "Yeni Müşteri A.Ş.", "city": "Ankara", "price_tier": "partner", "allow_backorder": True},
        )
        assert created.status_code == 200
        customer = created.json()
        assert customer["customer_id"].startswith("CUST-NEW-")
        assert re.fullmatch(r"CUST-NEW-\d{3}", customer["customer_id"])
        assert customer["customer_id"] not in {"CUST-ANK-002", "CUST-IST-001"}
        assert customer["name"] == "Yeni Müşteri A.Ş."
        assert customer["price_tier"] == "partner"
        assert customer["allow_backorder"] is True

        second_created = client.post(
            "/customers",
            json={"name": "Yeni Müşteri B", "city": "İzmir", "price_tier": "standard", "allow_backorder": False},
        )
        assert second_created.status_code == 200
        second_customer = second_created.json()
        assert re.fullmatch(r"CUST-NEW-\d{3}", second_customer["customer_id"])
        assert second_customer["customer_id"] != customer["customer_id"]

        refreshed = client.get("/customers").json()
        assert any(item["customer_id"] == customer["customer_id"] for item in refreshed)

        fetched = client.get(f"/customers/{customer['customer_id']}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Yeni Müşteri A.Ş."

        missing = client.get("/customers/CUST-NOPE-999")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_customer_quotes_are_scoped_and_create_quote(db):
    client = client_for(db)
    try:
        q1002 = client.get("/customers/CUST-ANK-002/quotes")
        assert q1002.status_code == 200
        assert q1002.json()
        assert all(item["customer_id"] == "CUST-ANK-002" for item in q1002.json())

        q1001 = client.get("/customers/CUST-IST-001/quotes")
        assert q1001.status_code == 200
        ank_ids = {item["quote_id"] for item in q1002.json()}
        ist_ids = {item["quote_id"] for item in q1001.json()}
        assert ank_ids.isdisjoint(ist_ids)

        created = client.post("/quotes", json={"customer_id": "CUST-ANK-002", "created_by_channel": "web"})
        assert created.status_code == 200
        quote = created.json()
        assert quote["quote_id"].startswith("Q-NEW-")
        assert re.fullmatch(r"Q-NEW-\d{3}", quote["quote_id"])
        assert quote["quote_id"] not in {"Q-1001", "Q-1002", "Q-1003", "Q-1004", "Q-1005"}
        assert quote["customer_id"] == "CUST-ANK-002"
        assert quote["status"] == "draft"
        assert quote["currency"] == "TRY"
        assert quote["items"] == []

        second_created = client.post("/quotes", json={"customer_id": "CUST-ANK-002", "created_by_channel": "mobile"})
        assert second_created.status_code == 200
        second_quote = second_created.json()
        assert re.fullmatch(r"Q-NEW-\d{3}", second_quote["quote_id"])
        assert second_quote["quote_id"] != quote["quote_id"]
        assert second_quote["customer_id"] == "CUST-ANK-002"

        refreshed = client.get("/customers/CUST-ANK-002/quotes").json()
        assert any(item["quote_id"] == quote["quote_id"] for item in refreshed)

        rejected = client.post("/quotes", json={"customer_id": "CUST-NOPE-999"})
        assert rejected.status_code == 400

        assert get_quote(db, quote["quote_id"]).data["customer_id"] == "CUST-ANK-002"
    finally:
        app.dependency_overrides.clear()


def test_chat_blocks_quote_from_another_customer_and_keeps_logs_visible(db):
    events = "".join(
        plan_and_execute(
            db,
            ChatStreamRequest(
                quote_id="Q-1002",
                customer_id="CUST-IST-001",
                session_id="SCOPE-1",
                message_id="SCOPE-1-M",
                message="BlueScan Air fiyatı ne kadar?",
            ),
        )
    )
    assert "Teklif bu müşteriye ait değil" in events

    ok_events = "".join(
        plan_and_execute(
            db,
            ChatStreamRequest(
                quote_id="Q-1002",
                customer_id="CUST-ANK-002",
                session_id="LOG-1",
                message_id="LOG-1-M",
                message="BlueScan Air fiyatı ne kadar ve stokta var mı?",
            ),
        )
    )
    assert "tool_call_result" in ok_events
    assert "quote_delta" in ok_events
    assert "source" in ok_events
    assert "fiyat" in ok_events

    client = client_for(db)
    try:
        all_logs = client.get("/tool-call-logs")
        assert all_logs.status_code == 200
        assert any(log["message_id"] == "LOG-1-M" for log in all_logs.json())

        session_logs = client.get("/sessions/LOG-1/tool-calls")
        assert session_logs.status_code == 200
        assert session_logs.json()
        assert all(log["session_id"] == "LOG-1" for log in session_logs.json())
    finally:
        app.dependency_overrides.clear()
