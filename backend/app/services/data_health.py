from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from .. import models as m
from ..data_layer.storage.metadata_store import MetadataStore
from ..data_layer.storage.paths import DataLayerPaths
from ..data_layer.warehouse.reader import WarehouseInstrument, WarehouseMarketDataStore
from ..utils import CN_TZ, dt_iso
from .stock_universe import MIN_MAIN_BOARD_COVERAGE, main_board_non_st_stocks


def get_data_health_overview(db: Session, *, data_root: Path = Path("data")) -> dict[str, Any]:
    store = WarehouseMarketDataStore(data_root)
    paths = DataLayerPaths(data_root)
    today = datetime.now(CN_TZ).date()
    main_board_stocks = main_board_non_st_stocks(store=store)
    expected_count = len(main_board_stocks)
    stock_codes = {stock.code for stock in main_board_stocks}

    open_dates = store.open_trade_dates(end_date=today)
    latest_open_date = open_dates[-1] if open_dates else None
    latest_price_date = store.latest_trade_date()
    coverage_date = latest_open_date or latest_price_date
    counts = store.daily_bar_counts_by_date(codes=stock_codes if stock_codes else None, end_date=coverage_date) if coverage_date else {}
    available_count = counts.get(coverage_date, 0) if coverage_date else 0
    coverage = available_count / expected_count if expected_count else 0

    latest_snapshot = (
        db.query(m.LimitUpBreakSnapshot)
        .order_by(m.LimitUpBreakSnapshot.trade_date.desc(), m.LimitUpBreakSnapshot.updated_at.desc())
        .first()
    )
    latest_run = _latest_sync_run(paths)

    return {
        "asOfDate": today.isoformat(),
        "calendar": {
            "todayIsOpen": latest_open_date == today,
            "latestOpenDate": latest_open_date.isoformat() if latest_open_date else None,
            "knownOpenDateCount": len(open_dates),
        },
        "dailyBars": {
            "status": _daily_bars_status(latest_open_date, latest_price_date, coverage, expected_count),
            "latestTradeDate": latest_price_date.isoformat() if latest_price_date else None,
            "coverageDate": coverage_date.isoformat() if coverage_date else None,
            "availableBars": available_count,
            "expectedBars": expected_count,
            "coverage": round(coverage, 4),
            "minCoverage": MIN_MAIN_BOARD_COVERAGE,
        },
        "sync": latest_run,
        "snapshot": _snapshot_payload(latest_snapshot, latest_open_date),
    }


def _daily_bars_status(latest_open_date, latest_price_date, coverage: float, expected_count: int) -> str:
    if latest_open_date is None or latest_price_date is None or expected_count == 0:
        return "MISSING"
    if latest_price_date < latest_open_date:
        return "STALE"
    if coverage < MIN_MAIN_BOARD_COVERAGE:
        return "INCOMPLETE"
    return "READY"


def _latest_sync_run(paths: DataLayerPaths) -> dict[str, Any] | None:
    metadata = MetadataStore(paths.sync_db)
    run = metadata.latest_run()
    if run is None:
        return None
    report = _read_sync_report(paths.metadata_root / "reports" / f"{run['id']}.json")
    return {
        "runId": run["id"],
        "provider": run["provider"],
        "jobType": run["job_type"],
        "status": run["status"],
        "startDate": run["start_date"],
        "endDate": run["end_date"],
        "startedAt": run["started_at"],
        "finishedAt": run["finished_at"],
        "errorMessage": run["error_message"],
        "successItems": report.get("success_items"),
        "failedItems": report.get("failed_items"),
        "skippedItems": report.get("skipped_items"),
        "warningCount": report.get("warning_count"),
    }


def _read_sync_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _snapshot_payload(snapshot: m.LimitUpBreakSnapshot | None, latest_open_date) -> dict[str, Any]:
    if snapshot is None:
        return {
            "status": "MISSING",
            "tradeDate": None,
            "updatedAt": None,
            "candidateCount": None,
            "breakCount": None,
            "suspendedBreakCount": None,
        }
    status = "READY" if latest_open_date is not None and snapshot.trade_date == latest_open_date else "STALE"
    return {
        "status": status,
        "tradeDate": snapshot.trade_date.isoformat(),
        "updatedAt": dt_iso(snapshot.updated_at),
        "candidateCount": snapshot.candidate_count,
        "breakCount": snapshot.break_count,
        "suspendedBreakCount": snapshot.suspended_break_count,
    }
