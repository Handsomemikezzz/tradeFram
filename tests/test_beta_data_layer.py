from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from backend.app import models as m
from backend.app.database import Base, engine, SessionLocal
from backend.app.main import app
from backend.app.providers.akshare_provider import AkShareMarketDataProvider
from backend.app.providers.base import MarketDataProvider, ProviderDailyBar, ProviderFinancialSnapshot, ProviderStockProfile
from backend.app.seed import seed_database
from backend.app.services.data_service import DataFetchError, fetch_market_dataset, normalize_stock_code
from backend.app.services.paper_trading import generate_ma_signal


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


class FailingProvider(MarketDataProvider):
    name = "FailingProvider"

    def get_stock_profile(self, code: str):
        raise RuntimeError("provider unavailable")

    def get_daily_bars(self, code: str, start_date: date, end_date: date):
        return []

    def get_financial_snapshot(self, code: str):
        return None

    def get_trading_calendar(self, start_date: date, end_date: date):
        return []


class EmptyBarsProvider(MarketDataProvider):
    name = "EmptyBarsProvider"

    def get_stock_profile(self, code: str):
        return ProviderStockProfile(code=code, symbol=f"{code}.SZ", exchange="SZ", name="空数据", market="测试", industry="测试")

    def get_daily_bars(self, code: str, start_date: date, end_date: date):
        return []

    def get_financial_snapshot(self, code: str):
        return ProviderFinancialSnapshot(code=code, pe=1, roe=1, revenue="1 亿", profit="1 亿", gross_margin=1, net_margin=1, report_period="2026-Q1")

    def get_trading_calendar(self, start_date: date, end_date: date):
        return []


class CountingProvider(MarketDataProvider):
    name = "CountingProvider"

    def __init__(self):
        self.profile_calls = 0
        self.bar_calls = 0

    def get_stock_profile(self, code: str):
        self.profile_calls += 1
        return ProviderStockProfile(code=code, symbol=f"{code}.SZ", exchange="SZ", name="计数测试", market="测试", industry="测试")

    def get_daily_bars(self, code: str, start_date: date, end_date: date):
        self.bar_calls += 1
        return bars_for([10.0] * 60)

    def get_financial_snapshot(self, code: str):
        return ProviderFinancialSnapshot(code=code, pe=1, roe=1, revenue="1 亿", profit="1 亿", gross_margin=1, net_margin=1, report_period="2026-Q1")

    def get_trading_calendar(self, start_date: date, end_date: date):
        return []


def bars_for(closes: list[float]) -> list[ProviderDailyBar]:
    start = date(2026, 1, 1)
    return [
        ProviderDailyBar(
            code="300750",
            trade_date=start + timedelta(days=i),
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
            volume=1000 + i,
            amount=(1000 + i) * close,
        )
        for i, close in enumerate(closes)
    ]


def test_stock_code_normalization():
    assert normalize_stock_code("300750") == ("300750", "300750.SZ", "SZ")
    assert normalize_stock_code("600519.SH") == ("600519", "600519.SH", "SH")
    assert normalize_stock_code("sz000858") == ("000858", "000858.SZ", "SZ")
    with pytest.raises(ValueError):
        normalize_stock_code("ABC123")


def test_data_source_failure_writes_data_fetch_log():
    reset_database()
    with SessionLocal() as db:
        with pytest.raises(DataFetchError):
            fetch_market_dataset(db, "300750", provider=FailingProvider())
        log = db.query(m.DataFetchLog).filter(m.DataFetchLog.provider == "FailingProvider").one()
        assert log.status == "FAILED"
        assert "provider unavailable" in (log.error_message or "")


def test_akshare_missing_dependency_returns_clear_error_and_fetch_log(monkeypatch):
    reset_database()

    def missing_akshare():
        raise RuntimeError("akshare is not installed; install requirements.txt and set AKSHARE_ENABLED=true")

    monkeypatch.setattr("backend.app.providers.akshare_provider._akshare", missing_akshare)
    with SessionLocal() as db:
        with pytest.raises(DataFetchError) as exc:
            fetch_market_dataset(db, "300750", provider=AkShareMarketDataProvider(), allow_stale_on_error=False)
        assert "akshare is not installed" in exc.value.message
        log = db.query(m.DataFetchLog).filter(m.DataFetchLog.provider == "AkShare").order_by(m.DataFetchLog.started_at.desc()).first()
        assert log is not None
        assert log.status == "FAILED"


def test_cache_hit_does_not_repeat_provider_request():
    reset_database()
    provider = CountingProvider()
    with SessionLocal() as db:
        first = fetch_market_dataset(db, "300750", provider=provider)
        second = fetch_market_dataset(db, "300750", provider=provider)
        assert first["usedCache"] is False
        assert second["usedCache"] is True
        assert provider.profile_calls == 1
        assert provider.bar_calls == 1


def test_expired_cache_refreshes_provider(monkeypatch):
    reset_database()
    monkeypatch.setenv("DATA_CACHE_TTL_MINUTES", "1440")
    provider = CountingProvider()
    with SessionLocal() as db:
        fetch_market_dataset(db, "300750", provider=provider)
        old_time = datetime.now(UTC) - timedelta(minutes=1441)
        for bar in db.query(m.PriceBar).filter(m.PriceBar.source == provider.name).all():
            bar.fetched_at = old_time
        db.commit()
        refreshed = fetch_market_dataset(db, "300750", provider=provider)
        assert refreshed["usedCache"] is False
        assert provider.profile_calls == 2
        assert provider.bar_calls == 2


def test_no_daily_data_research_task_fails_without_creating_report():
    reset_database()
    client = TestClient(app)
    response = client.post("/api/v1/research/tasks", json={"code": "300750", "options": {"provider": "empty"}})
    body = response.json()
    assert response.status_code == 422
    assert body["success"] is False
    assert body["error"]["code"] == "NO_DAILY_DATA"


def test_no_daily_data_signal_engine_returns_hold():
    reset_database()
    with SessionLocal() as db:
        db.query(m.PriceBar).delete()
        db.commit()
        stock = db.get(m.Stock, "300750")
        signal_type, reason, confidence = generate_ma_signal(db, stock)
        assert signal_type == "HOLD"
        assert confidence == 0.0
        assert "日线数据不足" in reason


def test_ma_strategy_generates_buy_sell_hold():
    assert generate_ma_signal(None, None, bars=bars_for([10.0] * 55 + [13.0, 14.0, 15.0, 16.0, 17.0]))[0] == "BUY"
    assert generate_ma_signal(None, None, bars=bars_for([20.0] * 55 + [15.0, 14.0, 13.0, 12.0, 11.0]))[0] == "SELL"
    assert generate_ma_signal(None, None, bars=bars_for([10.0] * 60))[0] == "HOLD"
