from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


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
        assert customer["name"] == "Yeni Müşteri A.Ş."
        assert customer["price_tier"] == "partner"
        assert customer["allow_backorder"] is True

        refreshed = client.get("/customers").json()
        assert any(item["customer_id"] == customer["customer_id"] for item in refreshed)
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
        assert quote["customer_id"] == "CUST-ANK-002"

        refreshed = client.get("/customers/CUST-ANK-002/quotes").json()
        assert any(item["quote_id"] == quote["quote_id"] for item in refreshed)

        rejected = client.post("/quotes", json={"customer_id": "CUST-NOPE-999"})
        assert rejected.status_code == 400
    finally:
        app.dependency_overrides.clear()
