from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd

from backend.app.data_layer.providers.base import (
    DataLayerDailyBar,
    DataLayerIndexDailyBar,
    DataLayerInstrument,
    DataLayerTradingDay,
)
from backend.app.data_layer.quality.validators import (
    validate_daily_bars,
    validate_index_daily_bars,
    validate_instruments,
    validate_trading_calendar,
)
from backend.app.data_layer.warehouse.normalize import (
    normalize_daily_bars,
    normalize_index_daily_bars,
    normalize_instruments,
    normalize_trading_calendar,
)
from backend.app.data_layer.warehouse.schemas import WAREHOUSE_SCHEMAS


def test_normalizers_emit_warehouse_schema_columns():
    updated_at = datetime(2026, 4, 30, tzinfo=UTC)
    instruments = normalize_instruments(
        [
            DataLayerInstrument(
                code="600519",
                symbol="600519.SH",
                exchange="SH",
                name="贵州茅台",
                market="主板",
                industry="白酒",
                list_date=date(2001, 8, 27),
                delist_date=None,
                status="active",
            )
        ],
        source_provider="akshare",
        source_updated_at=updated_at,
    )
    calendar = normalize_trading_calendar(
        [DataLayerTradingDay(trade_date=date(2026, 4, 30), exchange="CN_A", is_open=True)],
        source_provider="akshare",
        source_updated_at=updated_at,
    )
    bars = normalize_daily_bars(
        [
            DataLayerDailyBar(
                code="600519",
                symbol="600519.SH",
                exchange="SH",
                trade_date=date(2026, 4, 30),
                open=100,
                high=110,
                low=99,
                close=108,
                volume=1000,
                amount=108000,
            )
        ],
        source_provider="akshare",
        source_updated_at=updated_at,
    )
    indexes = normalize_index_daily_bars(
        [
            DataLayerIndexDailyBar(
                index_code="000001.SH",
                symbol="000001.SH",
                name="上证指数",
                trade_date=date(2026, 4, 30),
                open=3000,
                high=3010,
                low=2990,
                close=3005,
                volume=100,
                amount=100000,
            )
        ],
        source_provider="akshare",
        source_updated_at=updated_at,
    )

    assert list(instruments.columns) == WAREHOUSE_SCHEMAS["instruments"]
    assert list(calendar.columns) == WAREHOUSE_SCHEMAS["trading_calendar"]
    assert list(bars.columns) == WAREHOUSE_SCHEMAS["daily_bars"]
    assert list(indexes.columns) == WAREHOUSE_SCHEMAS["index_daily_bars"]
    assert instruments.loc[0, "source_provider"] == "akshare"


def test_validate_instruments_reports_errors_and_warnings():
    frame = pd.DataFrame(
        [
            {"code": "600519", "symbol": "600519.SH", "exchange": "SH", "name": "贵州茅台", "industry": ""},
            {"code": "600519", "symbol": "600519.SH", "exchange": "SH", "name": "重复", "industry": "白酒"},
            {"code": "ABC", "symbol": "ABC.SH", "exchange": "XX", "name": "", "industry": ""},
        ]
    )

    report = validate_instruments(frame)

    assert report.has_errors
    assert any(issue.code == "DUPLICATE_INSTRUMENT" for issue in report.errors)
    assert any(issue.code == "INVALID_CODE" for issue in report.errors)
    assert any(issue.code == "MISSING_INDUSTRY" for issue in report.warnings)


def test_validate_daily_bars_reports_invalid_ohlc_and_count_warnings():
    frame = pd.DataFrame(
        [
            {
                "code": "600519",
                "trade_date": date(2026, 4, 29),
                "price_adjustment": "none",
                "open": 100,
                "high": 99,
                "low": 101,
                "close": 100,
                "volume": -1,
                "amount": 10,
            },
            {
                "code": "600519",
                "trade_date": date(2026, 4, 29),
                "price_adjustment": "none",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 1,
                "amount": 10,
            },
            {
                "code": "000001",
                "trade_date": date(2026, 4, 30),
                "price_adjustment": "none",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10,
                "volume": 1,
                "amount": 10,
            },
        ]
    )

    report = validate_daily_bars(frame, expected_min_count_per_day=2)

    assert report.has_errors
    assert any(issue.code == "DUPLICATE_DAILY_BAR" for issue in report.errors)
    assert any(issue.code == "INVALID_OHLC" for issue in report.errors)
    assert any(issue.code == "NEGATIVE_VOLUME" for issue in report.errors)
    assert any(issue.code == "LOW_DAILY_COUNT" for issue in report.warnings)


def test_validate_calendar_and_index_bars():
    calendar_report = validate_trading_calendar(
        pd.DataFrame(
            [
                {"trade_date": date(2026, 4, 30), "is_open": True},
                {"trade_date": date(2026, 4, 30), "is_open": True},
            ]
        )
    )
    index_report = validate_index_daily_bars(
        pd.DataFrame(
            [
                {
                    "index_code": "000001.SH",
                    "trade_date": date(2026, 4, 30),
                    "open": 3000,
                    "high": 3010,
                    "low": 2990,
                    "close": 3005,
                    "volume": 100,
                    "amount": 1000,
                },
                {
                    "index_code": "000001.SH",
                    "trade_date": date(2026, 4, 30),
                    "open": 3000,
                    "high": 2990,
                    "low": 3010,
                    "close": 3005,
                    "volume": 100,
                    "amount": 1000,
                },
            ]
        )
    )

    assert any(issue.code == "DUPLICATE_TRADING_DAY" for issue in calendar_report.errors)
    assert any(issue.code == "DUPLICATE_INDEX_BAR" for issue in index_report.errors)
    assert any(issue.code == "INVALID_OHLC" for issue in index_report.errors)
