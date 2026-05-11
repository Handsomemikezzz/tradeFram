from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd

from backend.app.data_layer.providers.base import (
    DataLayerDailyBar,
    DataLayerIndexDailyBar,
    DataLayerInstrument,
    DataLayerTradingDay,
)
from backend.app.data_layer.storage.parquet_store import ParquetStore
from backend.app.data_layer.sync.jobs import SyncOptions, _merge_warehouse, init_history_data, sync_daily_data


class FakeDataLayerProvider:
    name = "fake"

    def __init__(self):
        self.daily_calls: list[str] = []

    def list_instruments(self):
        return [
            DataLayerInstrument("600519", "600519.SH", "SH", "贵州茅台", "主板", "白酒", None, None, "active"),
            DataLayerInstrument("000001", "000001.SZ", "SZ", "平安银行", "主板", "银行", None, None, "active"),
        ]

    def get_trading_calendar(self, start_date: date, end_date: date):
        return [
            DataLayerTradingDay(date(2026, 4, 28), "CN_A", True),
            DataLayerTradingDay(date(2026, 4, 29), "CN_A", True),
            DataLayerTradingDay(date(2026, 4, 30), "CN_A", True),
        ]

    def get_daily_bars(self, code: str, start_date: date, end_date: date, *, price_adjustment: str = "raw"):
        self.daily_calls.append(f"{code}:{price_adjustment}")
        return [
            DataLayerDailyBar(code, f"{code}.SH" if code.startswith("6") else f"{code}.SZ", "SH" if code.startswith("6") else "SZ", date(2026, 4, 29), 10, 11, 9, 10.5, 100, 1000, price_adjustment),
            DataLayerDailyBar(code, f"{code}.SH" if code.startswith("6") else f"{code}.SZ", "SH" if code.startswith("6") else "SZ", date(2026, 4, 30), 10.5, 12, 10, 11.5, 100, 1200, price_adjustment),
        ]

    def get_index_daily_bars(self, index_code: str, start_date: date, end_date: date):
        return [
            DataLayerIndexDailyBar(index_code, index_code, "指数", date(2026, 4, 30), 3000, 3010, 2990, 3005, 100, 100000)
        ]


class FakeBulkDataLayerProvider(FakeDataLayerProvider):
    def __init__(self):
        super().__init__()
        self.bulk_calls: list[str] = []

    def get_daily_bars_bulk(self, target_date: date, *, price_adjustment: str = "raw"):
        self.bulk_calls.append(f"{target_date.isoformat()}:{price_adjustment}")
        return [
            DataLayerDailyBar("600519", "600519.SH", "SH", target_date, 10, 11, 9, 10.5, 100, 1000, price_adjustment),
            DataLayerDailyBar("000001", "000001.SZ", "SZ", target_date, 11, 12, 10, 11.5, 200, 2000, price_adjustment),
        ]


class FakeWeekendBulkDataLayerProvider(FakeBulkDataLayerProvider):
    def get_trading_calendar(self, start_date: date, end_date: date):
        return [
            DataLayerTradingDay(date(2026, 5, 6), "CN_A", True),
            DataLayerTradingDay(date(2026, 5, 7), "CN_A", True),
            DataLayerTradingDay(date(2026, 5, 8), "CN_A", True),
            DataLayerTradingDay(date(2026, 5, 9), "CN_A", False),
            DataLayerTradingDay(date(2026, 5, 10), "CN_A", False),
        ]

    def get_daily_bars(self, code: str, start_date: date, end_date: date, *, price_adjustment: str = "raw"):
        self.daily_calls.append(f"{code}:{price_adjustment}")
        return [
            DataLayerDailyBar(code, f"{code}.SH" if code.startswith("6") else f"{code}.SZ", "SH" if code.startswith("6") else "SZ", end_date, 10, 11, 9, 10.5, 100, 1000, price_adjustment),
        ]


class MostlyFailingDataLayerProvider(FakeDataLayerProvider):
    def get_daily_bars(self, code: str, start_date: date, end_date: date, *, price_adjustment: str = "raw"):
        self.daily_calls.append(f"{code}:{price_adjustment}")
        raise ConnectionError("upstream disconnected")


def test_init_history_data_writes_limited_raw_warehouse_metadata_and_report(tmp_path):
    provider = FakeDataLayerProvider()
    result = init_history_data(
        SyncOptions(
            data_root=tmp_path / "data",
            provider_name="fake",
            start_date=date(2020, 1, 1),
            end_date=date(2026, 4, 30),
            limit=1,
        ),
        provider=provider,
    )

    assert result.status == "success"
    assert result.success_items >= 4
    assert result.failed_items == 0
    assert result.report_path.exists()
    assert provider.daily_calls == ["600519:raw"]
    assert (tmp_path / "data" / "raw" / "fake" / "daily_bars").exists()
    assert (tmp_path / "data" / "warehouse" / "daily_bars").exists()
    instruments = ParquetStore().read_dataset(tmp_path / "data" / "warehouse" / "instruments")
    assert list(instruments["code"]) == ["600519", "000001"]


def test_init_history_data_resume_skips_successful_items(tmp_path):
    provider = FakeDataLayerProvider()
    options = SyncOptions(
        data_root=tmp_path / "data",
        provider_name="fake",
        start_date=date(2020, 1, 1),
        end_date=date(2026, 4, 30),
        limit=1,
    )
    first = init_history_data(options, provider=provider)
    provider.daily_calls.clear()

    second = init_history_data(replace(options, resume=True, resume_run_id=first.run_id), provider=provider)

    assert second.skipped_items >= 1
    assert provider.daily_calls == []


def test_sync_daily_data_writes_recent_window_without_business_cache(tmp_path):
    result = sync_daily_data(
        SyncOptions(
            data_root=tmp_path / "data",
            provider_name="fake",
            end_date=date(2026, 4, 30),
            lookback_days=20,
        ),
        provider=FakeDataLayerProvider(),
    )

    assert result.status == "success"
    daily = ParquetStore().read_dataset(tmp_path / "data" / "warehouse" / "daily_bars")
    assert set(daily["code"]) == {"600519", "000001"}
    assert set(daily["price_adjustment"]) == {"raw"}


def test_sync_daily_data_uses_stable_per_stock_history_even_when_bulk_is_available(tmp_path):
    provider = FakeBulkDataLayerProvider()

    result = sync_daily_data(
        SyncOptions(
            data_root=tmp_path / "data",
            provider_name="fake",
            end_date=date(2026, 4, 30),
            lookback_days=20,
        ),
        provider=provider,
    )

    assert result.status == "success"
    assert provider.bulk_calls == []
    assert provider.daily_calls == ["600519:raw", "000001:raw"]
    daily = ParquetStore().read_dataset(tmp_path / "data" / "warehouse" / "daily_bars")
    assert set(daily["code"]) == {"600519", "000001"}


def test_sync_daily_data_on_weekend_backfills_latest_open_trading_day(tmp_path):
    provider = FakeWeekendBulkDataLayerProvider()

    result = sync_daily_data(
        SyncOptions(
            data_root=tmp_path / "data",
            provider_name="fake",
            end_date=date(2026, 5, 10),
            lookback_days=3,
        ),
        provider=provider,
    )

    assert result.status == "success"
    assert provider.bulk_calls == []
    assert provider.daily_calls == ["600519:raw", "000001:raw"]
    daily = ParquetStore().read_dataset(tmp_path / "data" / "warehouse" / "daily_bars")
    assert set(str(value) for value in daily["trade_date"]) == {"2026-05-08"}


def test_sync_daily_data_circuit_breaks_when_failure_rate_is_too_high(tmp_path):
    provider = MostlyFailingDataLayerProvider()

    result = sync_daily_data(
        SyncOptions(
            data_root=tmp_path / "data",
            provider_name="fake",
            end_date=date(2026, 4, 30),
            lookback_days=20,
            circuit_breaker_min_items=1,
            circuit_breaker_failure_rate=0.5,
        ),
        provider=provider,
    )

    assert result.status == "failed"
    assert result.failed_items >= 1
    assert provider.daily_calls == ["600519:raw"]


def test_merge_warehouse_reads_only_matching_partition(tmp_path):
    store = ParquetStore()
    path = tmp_path / "data" / "warehouse" / "daily_bars"
    existing = pd.DataFrame(
        [
            {"code": "600519", "trade_date": date(2026, 4, 29), "close": 10.5, "price_adjustment": "none"},
            {"code": "000001", "trade_date": date(2026, 4, 29), "close": 9.5, "price_adjustment": "none"},
        ]
    )
    store.write_dataset(path, existing, partition_cols=["code"], overwrite=True)
    calls: list[str] = []
    original_read_dataset = store.read_dataset

    def tracking_read_dataset(read_path):
        calls.append(str(read_path.relative_to(path)))
        return original_read_dataset(read_path)

    store.read_dataset = tracking_read_dataset
    _merge_warehouse(
        store,
        path,
        pd.DataFrame([{"code": "600519", "trade_date": date(2026, 4, 30), "close": 11.5, "price_adjustment": "none"}]),
        ["code", "trade_date", "price_adjustment"],
        partition_cols=["code"],
    )

    assert calls == ["code=600519"]
    result = store.read_dataset(path)
    assert len(result[result["code"] == "600519"]) == 2
    assert len(result[result["code"] == "000001"]) == 1
