from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.database import Base, engine
from backend.app.main import app
from backend.app.seed import seed_database


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


def payload(response):
    return response.json()


def assert_ok(response):
    body = payload(response)
    assert response.status_code == 200, body
    assert body["success"] is True, body
    return body["data"]


def assert_error(response, status_code: int, code: str):
    body = payload(response)
    assert response.status_code == status_code, body
    assert body["success"] is False, body
    assert body["error"]["code"] == code, body
    return body


def test_invalid_stock_code_returns_validation_or_not_found_error():
    reset_database()
    client = TestClient(app)

    invalid_format = client.post("/api/v1/research/tasks", json={"code": "ABC123"})
    assert_error(invalid_format, 422, "VALIDATION_ERROR")

    unknown_stock = client.post("/api/v1/research/tasks", json={"code": "999999"})
    assert_error(unknown_stock, 404, "STOCK_NOT_FOUND")


def test_duplicate_watchlist_and_monitoring_items_return_errors():
    reset_database()
    client = TestClient(app)

    assert_ok(client.post("/api/v1/watchlist/items", json={"code": "300750"}))
    assert_error(client.post("/api/v1/watchlist/items", json={"code": "300750"}), 409, "WATCHLIST_ALREADY_EXISTS")

    assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True}))
    assert_error(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True}), 409, "MONITORING_ITEM_ALREADY_EXISTS")


def test_risk_blocked_does_not_create_order_for_blocked_signal():
    reset_database()
    client = TestClient(app)

    assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "000858", "enabled": True}))
    run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"enabledOnly": True}}))
    assert run["summary"]["riskBlockedCount"] == 1
    assert run["summary"]["createdPaperOrderCount"] == 0

    orders = assert_ok(client.get("/api/v1/orders"))["items"]
    assert all(order["code"] != "000858" for order in orders)

    risks = assert_ok(client.get("/api/v1/risk-checks"))["items"]
    assert any(risk["code"] == "000858" and risk["status"] == "BLOCKED" for risk in risks)


def test_paper_trading_run_with_no_monitoring_stocks_completes_without_side_effect_orders():
    reset_database()
    client = TestClient(app)

    run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"enabledOnly": True}}))
    assert run["status"] == "COMPLETED"
    assert run["summary"]["scannedStockCount"] == 0
    assert run["summary"]["createdPaperOrderCount"] == 0
    assert assert_ok(client.get("/api/v1/orders"))["items"] == []


def test_report_not_found_returns_404():
    reset_database()
    client = TestClient(app)

    assert_error(client.get("/api/v1/research/reports/by-code/300750"), 404, "REPORT_NOT_FOUND")


def test_p0b_endpoints_return_expected_shapes():
    reset_database()
    client = TestClient(app)

    assert_ok(client.post("/api/v1/research/tasks", json={"code": "300750"}))
    assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True}))
    assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"enabledOnly": True}}))

    risk_status = assert_ok(client.get("/api/v1/risk/system-status"))
    assert "rules" in risk_status and risk_status["overallStatus"] in {"PASSED", "BLOCKED"}

    latest_trace = assert_ok(client.get("/api/v1/execution-traces/latest"))
    assert latest_trace["steps"][0]["step"] == "SIGNAL"

    overview = assert_ok(client.get("/api/v1/dashboard/overview"))
    assert "kpis" in overview and "tasks" in overview

    monitoring_summary = assert_ok(client.get("/api/v1/dashboard/monitoring-summary"))
    assert monitoring_summary["items"]

    stats = assert_ok(client.get("/api/v1/research/stats"))
    assert stats["researchCount"] >= 1


def test_frontend_does_not_expose_forbidden_trade_mutation_calls():
    forbidden = [
        "apiClient.post<OrderResponse>('/orders'",
        "apiClient.post('/orders'",
        "apiClient.post('/executions'",
        "apiClient.post('/positions'",
        "apiClient.post('/trade-logs'",
        "fetch('/api/v1/orders'",
        "fetch(\"/api/v1/orders\"",
    ]
    source = "\n".join(path.read_text() for path in Path("src").rglob("*.ts*") if "services/mock" not in str(path))
    for needle in forbidden:
        assert needle not in source
