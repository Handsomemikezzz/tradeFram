from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import Base, engine
from backend.app.seed import seed_database
from tests.akshare_fixture import install_akshare_fixture


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


def unwrap(response):
    payload = response.json()
    assert payload["success"] is True, payload
    assert "requestId" in payload
    assert "serverTime" in payload
    return payload["data"]


def test_paper_trading_run_executes_ordered_akshare_trade_loop(monkeypatch):
    reset_database()
    install_akshare_fixture(monkeypatch)
    client = TestClient(app)

    task = unwrap(client.post("/api/v1/research/tasks", json={"code": "300750"}))
    assert task["status"] == "COMPLETED"
    assert task["reportId"]

    report = unwrap(client.get("/api/v1/research/reports/by-code/300750"))
    assert report["code"] == "300750"
    assert report["report"]["aiDisclaimer"]

    watchlist_item = unwrap(client.post("/api/v1/watchlist/items", json={"code": "300750", "source": "TEST"}))
    assert watchlist_item["code"] == "300750"

    monitoring_item = unwrap(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True}))
    assert monitoring_item["enabled"] is True

    run = unwrap(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"enabledOnly": True}}))
    assert run["status"] == "COMPLETED"
    assert run["summary"]["generatedSignalCount"] >= 1
    assert run["summary"]["riskPassedCount"] >= 1
    assert run["summary"]["createdPaperOrderCount"] >= 1
    assert run["summary"]["simulatedExecutionCount"] >= 1

    orders = unwrap(client.get("/api/v1/orders"))["items"]
    assert any(order["code"] == "300750" and order["status"] == "FILLED" for order in orders)

    positions = unwrap(client.get("/api/v1/portfolio/positions"))["items"]
    assert any(position["code"] == "300750" and position["quantity"] > 0 for position in positions)

    risk_checks = unwrap(client.get("/api/v1/risk-checks"))["items"]
    assert any(check["code"] == "300750" and check["status"] == "PASSED" for check in risk_checks)

    logs = unwrap(client.get("/api/v1/logs"))["items"]
    events = [log["event"] for log in logs]
    assert "Signal Engine" in events
    assert "Risk Engine" in events
    assert "Order Manager" in events
    assert "Paper Broker" in events
    assert "Position Manager" in events
    assert "Trade Logger" in events
