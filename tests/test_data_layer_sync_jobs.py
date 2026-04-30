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
from backend.app.data_layer.sync.jobs import SyncOptions, init_history_data, sync_daily_data


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

    def get_daily_bars(self, code: str, start_date: date, end_date: date):
        self.daily_calls.append(code)
        return [
            DataLayerDailyBar(code, f"{code}.SH" if code.startswith("6") else f"{code}.SZ", "SH" if code.startswith("6") else "SZ", date(2026, 4, 29), 10, 11, 9, 10.5, 100, 1000),
            DataLayerDailyBar(code, f"{code}.SH" if code.startswith("6") else f"{code}.SZ", "SH" if code.startswith("6") else "SZ", date(2026, 4, 30), 10.5, 12, 10, 11.5, 100, 1200),
        ]

    def get_index_daily_bars(self, index_code: str, start_date: date, end_date: date):
        return [
            DataLayerIndexDailyBar(index_code, index_code, "指数", date(2026, 4, 30), 3000, 3010, 2990, 3005, 100, 100000)
        ]


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
    assert provider.daily_calls == ["600519"]
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


def test_sync_daily_data_writes_recent_window_and_backfill_is_explicit(tmp_path, monkeypatch):
    calls: list[str] = []

    def fake_backfill(**kwargs):
        calls.append(kwargs["provider_name"])

    monkeypatch.setattr("backend.app.data_layer.sync.jobs.backfill_business_cache", fake_backfill)
    result = sync_daily_data(
        SyncOptions(
            data_root=tmp_path / "data",
            provider_name="fake",
            end_date=date(2026, 4, 30),
            lookback_days=20,
            update_business_cache=True,
        ),
        provider=FakeDataLayerProvider(),
    )

    assert result.status == "success"
    assert calls == ["fake"]
    daily = ParquetStore().read_dataset(tmp_path / "data" / "warehouse" / "daily_bars")
    assert set(daily["code"]) == {"600519", "000001"}
