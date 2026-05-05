from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd

from backend.app import models as m
from backend.app.database import Base, SessionLocal, engine
from backend.app.data_layer.providers.base import (
    DataLayerDailyBar,
    DataLayerIndexDailyBar,
    DataLayerInstrument,
    DataLayerTradingDay,
)
from backend.app.data_layer.sync.business_cache import backfill_business_cache
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


def test_business_cache_rebuilds_price_bars_with_stable_ids(tmp_path):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    store = ParquetStore()
    instruments_path = tmp_path / "data" / "warehouse" / "instruments"
    daily_path = tmp_path / "data" / "warehouse" / "daily_bars"
    store.write_dataset(
        instruments_path,
        pd.DataFrame(
            [
                {
                    "code": "000001",
                    "symbol": "000001.SZ",
                    "exchange": "SZ",
                    "name": "平安银行",
                    "market": "主板",
                    "industry": "银行",
                }
            ]
        ),
        overwrite=True,
    )
    store.write_dataset(
        daily_path,
        pd.DataFrame(
            [
                _daily_row(date(2026, 4, 29), close=10, high=11, volume=100, amount=1000),
                _daily_row(date(2026, 4, 29), close=11, high=12, volume=200, amount=2000),
                _daily_row(date(2026, 4, 29), close=999, high=1, volume=1, amount=1, price_adjustment="qfq"),
                _daily_row(date(2026, 4, 30), close=12, high=12, volume=300, amount=3000),
            ]
        ),
        partition_cols=["code"],
        overwrite=True,
    )

    with SessionLocal() as db:
        db.add(m.Stock(code="000001", symbol="000001.SZ", exchange="SZ", name="旧名称", market="主板", industry="银行"))
        db.add(_price_bar("old_fake", date(2026, 4, 28), source="fake", close=1))
        db.add(_price_bar("other_provider", date(2026, 4, 28), source="other", close=2))
        db.commit()

    backfill_business_cache(data_root=tmp_path / "data", provider_name="fake")
    backfill_business_cache(data_root=tmp_path / "data", provider_name="fake")

    with SessionLocal() as db:
        fake_bars = db.query(m.PriceBar).filter(m.PriceBar.source == "fake").order_by(m.PriceBar.trade_date).all()
        assert [bar.id for bar in fake_bars] == ["bar_fake_000001_20260429", "bar_fake_000001_20260430"]
        assert [bar.close for bar in fake_bars] == [11, 12]
        assert db.query(m.PriceBar).filter(m.PriceBar.source == "other").count() == 1


def _daily_row(
    trade_date: date,
    *,
    close: float,
    high: float,
    volume: int,
    amount: float,
    price_adjustment: str = "none",
) -> dict:
    return {
        "code": "000001",
        "trade_date": trade_date,
        "open": 10,
        "high": high,
        "low": 9,
        "close": close,
        "volume": volume,
        "amount": amount,
        "price_adjustment": price_adjustment,
    }


def _price_bar(id_: str, trade_date: date, *, source: str, close: float) -> m.PriceBar:
    return m.PriceBar(
        id=id_,
        code="000001",
        trade_date=trade_date,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1,
        amount=1,
        source=source,
        price_adjustment="none",
    )
