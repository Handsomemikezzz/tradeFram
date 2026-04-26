from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect

from backend.app import models as m
from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.providers.base import MarketDataProvider, ProviderDailyBar, ProviderFinancialSnapshot, ProviderStockProfile
from backend.app.seed import seed_database
from backend.app.services.data_service import fetch_market_dataset


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


def assert_ok(response):
    body = response.json()
    assert response.status_code == 200, body
    assert body["success"] is True, body
    return body["data"]


class CountingProvider(MarketDataProvider):
    name = "RcProvider"

    def get_stock_profile(self, code: str):
        return ProviderStockProfile(code=code, symbol=f"{code}.SZ", exchange="SZ", name="RC测试", market="测试", industry="测试")

    def get_daily_bars(self, code: str, start_date: date, end_date: date):
        start = date(2026, 2, 25)
        return [
            ProviderDailyBar(code=code, trade_date=start + timedelta(days=i), open=10, high=11, low=9, close=10 + i * 0.1, volume=1000, amount=10000)
            for i in range(60)
        ]

    def get_financial_snapshot(self, code: str):
        return ProviderFinancialSnapshot(code=code, pe=1, roe=1, revenue="1 亿", profit="1 亿", gross_margin=1, net_margin=1, report_period="2026-Q1")

    def get_trading_calendar(self, start_date: date, end_date: date):
        return []


class FailingRcProvider(CountingProvider):
    def get_stock_profile(self, code: str):
        raise RuntimeError("rc provider failed")


def test_buy_quantity_must_be_a_share_lot_size():
    reset_database()
    client = TestClient(app)
    assert_ok(
        client.post(
            "/api/v1/monitoring-pool/items",
            json={"code": "300750", "enabled": True, "strategyParams": {"forceSignal": "BUY", "orderQuantity": 150}},
        )
    )

    run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"enabledOnly": True}}))
    assert run["summary"]["riskBlockedCount"] == 1
    risks = assert_ok(client.get("/api/v1/risk-checks"))["items"]
    assert any(risk["rule"] == "A_SHARE_LOT_SIZE" and risk["status"] == "BLOCKED" for risk in risks)


def test_buy_cash_insufficient_is_blocked():
    reset_database()
    with SessionLocal() as db:
        account = db.get(m.PaperAccount, "paper_default")
        account.cash = 1
        db.commit()
    client = TestClient(app)
    assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True, "strategyParams": {"forceSignal": "BUY", "orderQuantity": 100}}))

    run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"enabledOnly": True}}))
    assert run["summary"]["createdPaperOrderCount"] == 0
    risks = assert_ok(client.get("/api/v1/risk-checks"))["items"]
    assert any(risk["rule"] == "CASH_AVAILABLE" and risk["status"] == "BLOCKED" for risk in risks)


def test_sell_more_than_available_quantity_is_blocked():
    reset_database()
    client = TestClient(app)
    assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "601318", "enabled": True, "strategyParams": {"forceSignal": "SELL", "orderQuantity": 100}}))

    run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"enabledOnly": True}}))
    assert run["summary"]["createdPaperOrderCount"] == 0
    risks = assert_ok(client.get("/api/v1/risk-checks"))["items"]
    assert any(risk["rule"] == "SELL_POSITION_AVAILABLE" and risk["status"] == "BLOCKED" for risk in risks)


def test_t_plus_one_buy_position_is_not_immediately_sellable():
    reset_database()
    client = TestClient(app)
    item = assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True, "strategyParams": {"forceSignal": "BUY", "orderQuantity": 100}}))
    buy_run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"monitoringItemIds": [item["id"]], "enabledOnly": True}}))
    assert buy_run["summary"]["createdPaperOrderCount"] == 1

    with SessionLocal() as db:
        position = db.query(m.Position).filter(m.Position.code == "300750").one()
        assert position.quantity == 100
        assert position.available == 0
        monitoring_item = db.get(m.MonitoringItem, item["id"])
        monitoring_item.strategy_params = {"forceSignal": "SELL", "orderQuantity": 100}
        db.commit()

    sell_run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"monitoringItemIds": [item["id"]], "enabledOnly": True}}))
    assert sell_run["summary"]["riskBlockedCount"] == 1
    risks = assert_ok(client.get("/api/v1/risk-checks"))["items"]
    assert any(risk["rule"] == "SELL_POSITION_AVAILABLE" and "T+1" in risk["reason"] for risk in risks)


def test_no_market_data_blocks_execution():
    reset_database()
    with SessionLocal() as db:
        db.query(m.PriceBar).filter(m.PriceBar.code == "300750").delete()
        db.commit()
    client = TestClient(app)
    assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True}))
    run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"enabledOnly": True}}))
    assert run["summary"]["createdPaperOrderCount"] == 0
    risks = assert_ok(client.get("/api/v1/risk-checks"))["items"]
    assert any(risk["rule"] == "DATA_UNAVAILABLE" and risk["status"] == "BLOCKED" for risk in risks)


def test_data_status_api_returns_rc_diagnostics():
    reset_database()
    client = TestClient(app)
    status = assert_ok(client.get("/api/v1/data/stocks/300750/status?provider=mock"))
    for key in [
        "provider",
        "code",
        "symbol",
        "lastFetchedAt",
        "latestTradeDate",
        "priceBarCount",
        "financialSnapshotAvailable",
        "cacheHit",
        "dataStale",
        "dataCompleteness",
        "lastError",
    ]:
        assert key in status


def test_failed_refresh_keeps_old_cache():
    reset_database()
    with SessionLocal() as db:
        first = fetch_market_dataset(db, "300750", provider=CountingProvider(), force_refresh=True)
        assert first["usedCache"] is False
        old_time = datetime.now(UTC) - timedelta(minutes=1441)
        for bar in db.query(m.PriceBar).filter(m.PriceBar.source == "RcProvider").all():
            bar.fetched_at = old_time
        db.commit()
        stale = fetch_market_dataset(db, "300750", provider=FailingRcProvider(), force_refresh=True, allow_stale_on_error=True)
        assert stale["usedCache"] is True
        assert stale["dataStale"] is True
        assert stale["refreshError"] == "rc provider failed"
        assert db.query(m.PriceBar).filter(m.PriceBar.source == "RcProvider").count() == 60


def test_alembic_baseline_can_create_tables(tmp_path, monkeypatch):
    db_file = tmp_path / "baseline.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    tables = set(inspect(create_engine(f"sqlite:///{db_file}")).get_table_names())
    assert {"stock", "paper_order", "paper_execution", "price_bar", "data_fetch_log"}.issubset(tables)


def test_buy_fee_fields_and_cash_deduction_are_correct():
    reset_database()
    client = TestClient(app)
    item = assert_ok(
        client.post(
            "/api/v1/monitoring-pool/items",
            json={
                "code": "300750",
                "enabled": True,
                "strategyParams": {"forceSignal": "BUY", "orderQuantity": 100},
                "riskParams": {"maxOrderValue": 100000, "maxSingleStockPositionValue": 100000, "slippageRate": 0.001, "commissionRate": 0.001, "minCommission": 5},
            },
        )
    )
    run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"monitoringItemIds": [item["id"]], "enabledOnly": True}}))
    assert run["summary"]["createdPaperOrderCount"] == 1
    order = assert_ok(client.get("/api/v1/orders"))["items"][0]
    assert order["rawPrice"] == order["price"]
    assert order["executedPrice"] > order["rawPrice"]
    assert order["commission"] >= 5
    assert order["stampTax"] == 0
    assert order["totalFee"] == order["commission"]
    assert order["netAmount"] == round(order["finalAmount"] + order["totalFee"], 2)
    account = assert_ok(client.get("/api/v1/portfolio/account-summary"))
    assert round(account["availableCash"], 2) == round(1_000_000 - order["netAmount"], 2)


def test_sell_fee_fields_and_cash_credit_are_correct():
    reset_database()
    with SessionLocal() as db:
        account = db.get(m.PaperAccount, "paper_default")
        stock = db.get(m.Stock, "300750")
        db.add(m.Position(id=f"pos_{account.id}_300750", account_id=account.id, code="300750", quantity=200, available=200, cost_price=100, current_price=stock.price, market_value=200 * stock.price))
        db.commit()
    client = TestClient(app)
    item = assert_ok(
        client.post(
            "/api/v1/monitoring-pool/items",
            json={
                "code": "300750",
                "enabled": True,
                "strategyParams": {"forceSignal": "SELL", "orderQuantity": 100},
                "riskParams": {"slippageRate": 0.001, "commissionRate": 0.001, "stampTaxRate": 0.001, "minCommission": 5},
            },
        )
    )
    run = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"monitoringItemIds": [item["id"]], "enabledOnly": True}}))
    assert run["summary"]["createdPaperOrderCount"] == 1
    order = assert_ok(client.get("/api/v1/orders"))["items"][0]
    assert order["executedPrice"] < order["rawPrice"]
    assert order["commission"] >= 5
    assert order["stampTax"] > 0
    assert order["totalFee"] == round(order["commission"] + order["stampTax"], 2)
    assert order["netAmount"] == round(order["finalAmount"] - order["totalFee"], 2)
    account = assert_ok(client.get("/api/v1/portfolio/account-summary"))
    assert round(account["availableCash"], 2) == round(1_000_000 + order["netAmount"], 2)


def test_strict_trading_time_blocks_and_demo_mode_allows(monkeypatch):
    reset_database()
    client = TestClient(app)
    item = assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True, "strategyParams": {"forceSignal": "BUY", "orderQuantity": 100}}))

    monkeypatch.setenv("STRICT_TRADING_TIME_CHECK", "true")
    monkeypatch.setenv("ALLOW_MANUAL_RUN_OUTSIDE_TRADING_TIME", "true")
    blocked = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"monitoringItemIds": [item["id"]], "enabledOnly": True}}))
    assert blocked["summary"]["createdPaperOrderCount"] == 0
    risks = assert_ok(client.get("/api/v1/risk-checks"))["items"]
    assert any(risk["rule"] == "TRADING_TIME" and risk["status"] == "BLOCKED" for risk in risks)

    reset_database()
    client = TestClient(app)
    item = assert_ok(client.post("/api/v1/monitoring-pool/items", json={"code": "300750", "enabled": True, "strategyParams": {"forceSignal": "BUY", "orderQuantity": 100}}))
    monkeypatch.setenv("STRICT_TRADING_TIME_CHECK", "false")
    monkeypatch.setenv("ALLOW_MANUAL_RUN_OUTSIDE_TRADING_TIME", "true")
    allowed = assert_ok(client.post("/api/v1/paper-trading/runs", json={"trigger": "MANUAL", "scope": {"monitoringItemIds": [item["id"]], "enabledOnly": True}}))
    assert allowed["summary"]["createdPaperOrderCount"] == 1
