from __future__ import annotations

from abc import ABC
from datetime import date

import pytest

from backend.app.data_layer.providers.base import (
    DataLayerDailyBar,
    DataLayerInstrument,
    DataLayerProvider,
)
from backend.app.data_layer.warehouse.schemas import CORE_INDEXES, WAREHOUSE_SCHEMAS


def test_data_layer_provider_defines_full_market_boundary():
    assert issubclass(DataLayerProvider, ABC)
    for method in ["list_instruments", "get_trading_calendar", "get_daily_bars", "get_index_daily_bars"]:
        assert method in DataLayerProvider.__abstractmethods__


def test_data_layer_records_capture_internal_shapes():
    instrument = DataLayerInstrument(
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
    bar = DataLayerDailyBar(
        code="600519",
        symbol="600519.SH",
        exchange="SH",
        trade_date=date(2026, 4, 30),
        open=100.0,
        high=110.0,
        low=99.0,
        close=108.0,
        volume=1000,
        amount=108000.0,
        price_adjustment="none",
    )

    assert instrument.symbol == "600519.SH"
    assert bar.price_adjustment == "none"


@pytest.mark.parametrize(
    ("dataset", "columns"),
    [
        (
            "instruments",
            [
                "code",
                "symbol",
                "exchange",
                "name",
                "market",
                "industry",
                "list_date",
                "delist_date",
                "status",
                "source_provider",
                "source_updated_at",
            ],
        ),
        (
            "trading_calendar",
            ["trade_date", "exchange", "is_open", "source_provider", "source_updated_at"],
        ),
        (
            "daily_bars",
            [
                "code",
                "symbol",
                "exchange",
                "trade_date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "price_adjustment",
                "source_provider",
                "source_updated_at",
            ],
        ),
        (
            "index_daily_bars",
            [
                "index_code",
                "symbol",
                "name",
                "trade_date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "source_provider",
                "source_updated_at",
            ],
        ),
        (
            "adj_factors",
            ["code", "symbol", "trade_date", "adj_factor", "source_provider", "source_updated_at"],
        ),
    ],
)
def test_warehouse_schemas_are_stable_contracts(dataset: str, columns: list[str]):
    assert WAREHOUSE_SCHEMAS[dataset] == columns


def test_core_indexes_cover_first_phase_scope():
    assert CORE_INDEXES == {
        "000001.SH": "上证指数",
        "000002.SH": "上证A股指数",
        "399001.SZ": "深证成指",
        "399107.SZ": "深证A股指数",
        "399006.SZ": "创业板指",
        "000300.SH": "沪深300",
        "000905.SH": "中证500",
        "000852.SH": "中证1000",
    }
