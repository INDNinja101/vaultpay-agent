"""End-to-end gate test in MOCK PayPal mode (Blueprint Gate 17):
ALLOW pays (mock COMPLETED) - ASK pauses creating an approval -
DENY creates NO order. Also verifies approval -> capture flow.
Runs against a fresh temp SQLite DB via FastAPI TestClient.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["PAYPAL_MOCK"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_e2e.db"

import pytest
from fastapi.testclient import TestClient

for f in ("test_e2e.db",):
    if os.path.exists(f):
        os.remove(f)

import main as main_mod
import models
from db import SessionLocal

client = TestClient(main_mod.app)


@pytest.fixture(autouse=True)
def fresh():
    with client:  # triggers startup (init + seed)
        r = client.post("/api/demo/reset")
        assert r.status_code == 200
        yield


def _orders_for(task_id):
    db = SessionLocal()
    try:
        return db.query(models.Order).filter_by(task_id=task_id).all()
    finally:
        db.close()


def test_health():
    r = client.get("/health")
    assert r.json()["ok"] is True and r.json()["paypal_mock"] is True


def test_policy_parse_fallback():
    r = client.post("/api/policies/parse", json={
        "text": "Fest supplies under $60, ask me above $25, never subscriptions, only sellers rated 4+"})
    p = r.json()["policy_json"]
    assert p["total_budget_usd"] == 60 and p["per_item_ask_above_usd"] == 25
    assert p["blocked_categories"] == ["subscription"] and p["min_seller_rating"] == 4.0


def test_allow_pays_mock_completed():
    r = client.post("/api/tasks", json={"prompt": "buy LED String Lights 10m for the fest"})
    assert r.status_code == 200
    tid = r.json()["task_id"]
    task = client.get(f"/api/tasks/{tid}").json()
    assert task["status"] == "COMPLETED"
    assert task["spent_total"] == 18.0
    orders = _orders_for(tid)
    assert len(orders) == 1 and orders[0].status == "PAID"
    assert orders[0].paypal_order_id.startswith("MOCK-")
    audit = client.get("/api/audit", params={"task_id": tid}).json()["events"]
    assert any(e["type"] == "PAID" and "COMPLETED" in e["message"] for e in audit)


def test_ask_pauses_then_approval_pays():
    r = client.post("/api/tasks", json={"prompt": "buy Premium Gift Hamper"})
    tid = r.json()["task_id"]
    assert r.json()["status"] == "WAITING_APPROVAL"
    assert _orders_for(tid) == []  # nothing paid yet
    approvals = client.get("/api/approvals").json()["approvals"]
    mine = [a for a in approvals if a["task_id"] == tid]
    assert len(mine) == 1 and mine[0]["item"]["price"] == 31.0
    d = client.post(f"/api/approvals/{mine[0]['id']}", json={"decision": "APPROVE"})
    assert d.json()["candidate_status"] == "PAID"
    orders = _orders_for(tid)
    assert len(orders) == 1 and orders[0].status == "PAID"


def test_deny_creates_no_order():
    r = client.post("/api/tasks", json={"prompt": "buy a streaming subscription"})
    tid = r.json()["task_id"]
    task = client.get(f"/api/tasks/{tid}").json()
    assert task["status"] == "BLOCKED"
    assert _orders_for(tid) == []  # DENY: no PayPal order ever created
    audit = client.get("/api/audit", params={"task_id": tid}).json()["events"]
    assert any(e["type"] == "DENY" and "blocked category" in e["message"] for e in audit)


def test_webhook_idempotent_in_mock():
    body = {"id": "WH-E2E-1", "event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "MOCK-X"}}
    assert client.post("/api/paypal/webhook", json=body).json()["ok"] is True
    assert client.post("/api/paypal/webhook", json=body).json().get("duplicate") is True
