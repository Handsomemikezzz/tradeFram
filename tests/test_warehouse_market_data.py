from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd

from backend.app.data_layer.storage.parquet_store import ParquetStore
from backend.app.data_layer.warehouse.reader import WarehouseIndexBar, WarehouseMarketDataStore


def test_warehouse_reader_returns_recent_raw_bars_without_sqlite(tmp_path):
    store = ParquetStore()
    daily_path = tmp_path / "data" / "warehouse" / "daily_bars"
    store.write_dataset(
        daily_path,
        pd.DataFrame(
            [
                _row("600001", date(2026, 4, 28), 10, "raw"),
                _row("600001", date(2026, 4, 29), 11, "qfq"),
                _row("600001", date(2026, 4, 29), 12, "raw"),
                _row("600002", date(2026, 4, 29), 20, "raw"),
                _row("600001", date(2026, 4, 30), 13, "raw"),
            ]
        ),
        partition_cols=["code"],
        overwrite=True,
    )

    bars = WarehouseMarketDataStore(tmp_path / "data").get_daily_bars("600001", limit=2, price_adjustment="raw")

    assert [bar.trade_date for bar in bars] == [date(2026, 4, 29), date(2026, 4, 30)]
    assert [bar.close for bar in bars] == [12, 13]
    assert bars[0].source == "warehouse"
    assert bars[0].price_adjustment == "raw"


def test_warehouse_reader_exposes_trade_dates_and_latest_bar(tmp_path):
    store = ParquetStore()
    daily_path = tmp_path / "data" / "warehouse" / "daily_bars"
    store.write_dataset(
        daily_path,
        pd.DataFrame(
            [
                _row("600001", date(2026, 4, 28), 10, "raw"),
                _row("600001", date(2026, 4, 29), 11, "raw"),
                _row("600002", date(2026, 4, 30), 20, "raw"),
            ]
        ),
        partition_cols=["code"],
        overwrite=True,
    )
    reader = WarehouseMarketDataStore(tmp_path / "data")

    assert reader.trade_dates(end_date=date(2026, 4, 29)) == [date(2026, 4, 28), date(2026, 4, 29)]
    assert reader.latest_trade_date() == date(2026, 4, 30)
    assert reader.get_bar("600002", date(2026, 4, 30)).close == 20


def test_get_index_daily_bars_reads_partitioned_index_data(tmp_path):
    store = ParquetStore()
    data_root = tmp_path / "data"
    path = data_root / "warehouse" / "index_daily_bars"
    frame = pd.DataFrame(
        [
            {
                "index_code": "000002.SH",
                "symbol": "000002.SH",
                "name": "上证A股指数",
                "trade_date": date(2026, 5, 18),
                "open": 3100.0,
                "high": 3120.0,
                "low": 3090.0,
                "close": 3110.0,
                "volume": 100,
                "amount": 100000.0,
                "source_provider": "fake",
                "source_updated_at": datetime(2026, 5, 18, tzinfo=UTC),
            },
            {
                "index_code": "399107.SZ",
                "symbol": "399107.SZ",
                "name": "深证A股指数",
                "trade_date": date(2026, 5, 18),
                "open": 2000.0,
                "high": 2010.0,
                "low": 1990.0,
                "close": 2005.0,
                "volume": 100,
                "amount": 100000.0,
                "source_provider": "fake",
                "source_updated_at": datetime(2026, 5, 18, tzinfo=UTC),
            },
        ]
    )
    store.write_dataset(path, frame, overwrite=True, partition_cols=["index_code"])

    bars = WarehouseMarketDataStore(data_root).get_index_daily_bars(
        "000002.SH",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    assert len(bars) == 1
    assert bars[0].index_code == "000002.SH"
    assert bars[0].name == "上证A股指数"
    assert bars[0].close == 3110.0


def _row(code: str, trade_date: date, close: float, price_adjustment: str) -> dict:
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
        "price_adjustment": price_adjustment,
        "source_provider": "fake",
        "source_updated_at": datetime(2026, 5, 5, tzinfo=UTC),
    }
