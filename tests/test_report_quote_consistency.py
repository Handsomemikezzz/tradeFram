from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd

from backend.app import models as m
from backend.app.data_layer.storage.parquet_store import ParquetStore
from backend.app.data_layer.warehouse.reader import WarehouseMarketDataStore
from backend.app.serializers import quote_payload, research_report_payload, trend_payload


def _write_bars(tmp_path, rows: list[dict]) -> None:
    store = ParquetStore()
    daily_path = tmp_path / "data" / "warehouse" / "daily_bars"
    store.write_dataset(daily_path, pd.DataFrame(rows), partition_cols=["code"], overwrite=True)


def test_quote_and_trend_use_same_warehouse_latest_close(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    _write_bars(
        tmp_path,
        [
            _row("600001", date(2026, 4, 28), 89.10),
            _row("600001", date(2026, 5, 16), 107.00),
        ],
    )
    stock = m.Stock(
        code="600001",
        symbol="600001.SH",
        exchange="SH",
        name="测试股",
        market="A",
        industry="测试",
        price=89.10,
        change=0.0,
        change_percent=0.0,
        volume=1000,
        amount=100000.0,
        update_time=datetime(2026, 4, 25, tzinfo=UTC),
    )

    quote = quote_payload(stock)
    trend = trend_payload(stock)

    assert quote["price"] == 107.0
    assert trend[-1]["price"] == 107.0


def test_research_report_merges_live_price_insight(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    _write_bars(
        tmp_path,
        [
            _row("600001", date(2026, 5, 12), 100.0),
            _row("600001", date(2026, 5, 13), 101.0),
            _row("600001", date(2026, 5, 14), 102.0),
            _row("600001", date(2026, 5, 15), 103.0),
            _row("600001", date(2026, 5, 16), 107.0),
        ],
    )
    stock = m.Stock(
        code="600001",
        symbol="600001.SH",
        exchange="SH",
        name="测试股",
        market="A",
        industry="测试",
        price=89.10,
        change=0.0,
        change_percent=0.0,
        volume=1000,
        amount=100000.0,
        update_time=datetime(2026, 4, 25, tzinfo=UTC),
    )
    report = m.ResearchReport(
        id="rr-test",
        task_id="rt-test",
        code="600001",
        status="COMPLETED",
        overview="概览",
        key_insights=["行业属性：测试。", "最新收盘价：89.10；MA5=88.00，MA20=85.00。"],
        risks=[],
        business_segments=[],
        news_items=[],
        worth_further_research=True,
        ai_confidence=0.0,
        data_completeness=0.8,
        ai_disclaimer="免责声明",
        research_base_period="2025Q4",
        data_sources=["AkShare"],
        generated_at=datetime(2026, 4, 25, tzinfo=UTC),
    )
    report.stock = stock

    payload = research_report_payload(report)
    price_insight = next(item for item in payload["report"]["keyInsights"] if item.startswith("最新收盘价："))

    assert payload["quote"]["price"] == 107.0
    assert "107.00" in price_insight
    assert "89.10" not in price_insight


def _row(code: str, trade_date: date, close: float) -> dict:
    return {
        "code": code,
        "symbol": f"{code}.SH",
        "exchange": "SH",
        "trade_date": trade_date,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 1000,
        "amount": close * 1000,
        "price_adjustment": "raw",
        "source_provider": "fake",
        "source_updated_at": datetime(2026, 5, 16, tzinfo=UTC),
    }
