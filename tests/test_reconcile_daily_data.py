from __future__ import annotations

from datetime import UTC, date, datetime
import os
from pathlib import Path

import pandas as pd
import pytest

from backend.app import models as m
from backend.app.data_layer.storage.parquet_store import ParquetStore
from backend.app.data_layer.sync.jobs import SyncResult
from backend.app.database import Base, SessionLocal, engine
from backend.app.seed import seed_database
from scripts import reconcile_daily_data as reconcile


@pytest.fixture()
def isolated_data_root(tmp_path, monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()
    data_root = tmp_path / "data"
    monkeypatch.setenv("DATA_ROOT", str(data_root))
    return data_root


def write_instruments(data_root: Path) -> None:
    rows = [
        instrument("600001", "主板一", "SH"),
        instrument("600002", "主板二", "SH"),
        instrument("000001", "主板三", "SZ"),
        instrument("002001", "主板四", "SZ"),
        instrument("603001", "主板五", "SH"),
        instrument("300001", "创业板", "SZ"),
        instrument("688001", "科创板", "SH"),
        instrument("600003", "ST样本", "SH"),
    ]
    ParquetStore().write_dataset(data_root / "warehouse" / "instruments", pd.DataFrame(rows), overwrite=True)


def instrument(code: str, name: str, exchange: str) -> dict:
    return {
        "code": code,
        "symbol": f"{code}.{exchange}",
        "exchange": exchange,
        "name": name,
        "market": "主板",
        "industry": "测试",
        "list_date": None,
        "delist_date": None,
        "status": "active",
        "source_provider": "fake",
        "source_updated_at": datetime(2026, 5, 19, tzinfo=UTC),
    }


def write_calendar(data_root: Path) -> None:
    rows = [
        {"trade_date": date(2026, 5, 15), "exchange": "CN_A", "is_open": True, "source_provider": "fake", "source_updated_at": datetime(2026, 5, 19, tzinfo=UTC)},
        {"trade_date": date(2026, 5, 18), "exchange": "CN_A", "is_open": True, "source_provider": "fake", "source_updated_at": datetime(2026, 5, 19, tzinfo=UTC)},
        {"trade_date": date(2026, 5, 19), "exchange": "CN_A", "is_open": True, "source_provider": "fake", "source_updated_at": datetime(2026, 5, 19, tzinfo=UTC)},
        {"trade_date": date(2026, 5, 20), "exchange": "CN_A", "is_open": False, "source_provider": "fake", "source_updated_at": datetime(2026, 5, 19, tzinfo=UTC)},
    ]
    ParquetStore().write_dataset(data_root / "warehouse" / "trading_calendar", pd.DataFrame(rows), overwrite=True)


def write_bars(data_root: Path, codes: list[str], dates: list[date]) -> None:
    rows = []
    for code in codes:
        exchange = "SH" if code.startswith("6") else "SZ"
        for offset, trade_date in enumerate(dates):
            close = 10.0 + offset / 10
            rows.append(
                {
                    "code": code,
                    "symbol": f"{code}.{exchange}",
                    "exchange": exchange,
                    "trade_date": trade_date,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": 1000,
                    "amount": 10000,
                    "price_adjustment": "raw",
                    "source_provider": "fake",
                    "source_updated_at": datetime(2026, 5, 19, tzinfo=UTC),
                }
            )
    ParquetStore().write_dataset(data_root / "warehouse" / "daily_bars", pd.DataFrame(rows), partition_cols=["code"], overwrite=True)


def fake_sync_result(data_root: Path) -> SyncResult:
    report_path = data_root / "metadata" / "reports" / "fake.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("{}", encoding="utf-8")
    return SyncResult("run_fake", "fake", "sync_daily_data", "success", 1, 0, 0, 0, report_path)


def test_target_trade_date_uses_latest_open_day_before_midnight_date(isolated_data_root):
    write_calendar(isolated_data_root)

    target = reconcile.resolve_target_trade_date(
        isolated_data_root,
        now=datetime(2026, 5, 20, 0, 0, tzinfo=reconcile.CN_TZ),
    )

    assert target == date(2026, 5, 19)


def test_coverage_counts_only_main_board_non_st(isolated_data_root):
    write_instruments(isolated_data_root)
    write_calendar(isolated_data_root)
    write_bars(isolated_data_root, ["600001", "600002", "000001", "300001", "688001", "600003"], [date(2026, 5, 19)])

    coverage = reconcile.calculate_main_board_coverage(isolated_data_root, date(2026, 5, 19))

    assert coverage.expected_bars == 5
    assert coverage.available_bars == 3
    assert coverage.coverage == 0.6


def test_reconcile_returns_incomplete_without_snapshot_when_coverage_is_low(isolated_data_root, monkeypatch):
    write_instruments(isolated_data_root)
    write_calendar(isolated_data_root)
    write_bars(isolated_data_root, ["600001", "600002", "000001"], [date(2026, 5, 18), date(2026, 5, 19)])
    monkeypatch.setattr(reconcile, "sync_daily_data", lambda *args, **kwargs: fake_sync_result(isolated_data_root))

    exit_code = reconcile.run(
        [
            "--data-root",
            str(isolated_data_root),
            "--provider",
            "akshare",
            "--now",
            "2026-05-20T00:00:00+08:00",
        ]
    )

    assert exit_code == 1
    with SessionLocal() as db:
        assert db.query(m.LimitUpBreakSnapshot).count() == 0


def test_reconcile_generates_snapshot_for_latest_open_trade_date_when_coverage_is_ready(isolated_data_root, monkeypatch):
    write_instruments(isolated_data_root)
    write_calendar(isolated_data_root)
    main_codes = ["600001", "600002", "000001", "002001", "603001"]
    write_bars(isolated_data_root, main_codes, [date(2026, 5, 15), date(2026, 5, 18), date(2026, 5, 19)])
    monkeypatch.setattr(reconcile, "sync_daily_data", lambda *args, **kwargs: fake_sync_result(isolated_data_root))

    exit_code = reconcile.run(
        [
            "--data-root",
            str(isolated_data_root),
            "--provider",
            "akshare",
            "--now",
            "2026-05-20T00:00:00+08:00",
        ]
    )

    assert exit_code == 0
    with SessionLocal() as db:
        snapshot = db.query(m.LimitUpBreakSnapshot).one()
        assert snapshot.trade_date == date(2026, 5, 19)
        assert snapshot.candidate_count == 0
