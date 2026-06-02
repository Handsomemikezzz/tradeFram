from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models as m
from ..schemas import ScreenerSnapshotCreate
from ..serializers_screeners import screener_item_detail_payload, screener_snapshot_payload
from ..services.daily_bars import DailyBarError, daily_bar_payload, get_daily_bar_series
from ..services.pattern_a import PATTERN_A_STRATEGY_TYPE
from ..services.screeners import (
    ScreenerError,
    SUPPORTED_STRATEGIES,
    generate_pattern_a_snapshot,
    get_default_screener_snapshot,
    get_screener_item,
    get_screener_snapshot,
)
from ..utils import api_error, ok

router = APIRouter()


@router.post("/screeners/snapshots")
def create_screener_snapshot(payload: ScreenerSnapshotCreate, db: Session = Depends(get_db)):
    if payload.strategyType not in SUPPORTED_STRATEGIES:
        raise api_error(400, "SCREENER_UNSUPPORTED_STRATEGY", f"暂不支持的策略类型: {payload.strategyType}")
    try:
        snapshot = generate_pattern_a_snapshot(db, payload.tradeDate, provider=payload.provider)
        db.commit()
        db.refresh(snapshot)
    except ScreenerError as exc:
        db.rollback()
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc
    return ok(screener_snapshot_payload(snapshot, db))


@router.get("/screeners/snapshots/default/latest")
def read_default_screener_snapshot(
    strategyType: str = Query(PATTERN_A_STRATEGY_TYPE),
    provider: str = Query("AkShare"),
    db: Session = Depends(get_db),
):
    snapshot, target_date = get_default_screener_snapshot(db, strategy_type=strategyType, provider=provider)
    if target_date is None:
        raise api_error(404, "SCREENER_SNAPSHOT_NOT_FOUND", "无默认选股快照日期")
    if snapshot is None:
        raise api_error(404, "SCREENER_SNAPSHOT_NOT_FOUND", f"{target_date.isoformat()} 选股快照不存在")
    return ok(screener_snapshot_payload(snapshot, db))


@router.get("/screeners/snapshots/{trade_date}")
def read_screener_snapshot(
    trade_date: date,
    strategyType: str = Query(PATTERN_A_STRATEGY_TYPE),
    provider: str = Query("AkShare"),
    db: Session = Depends(get_db),
):
    snapshot = get_screener_snapshot(db, trade_date, strategy_type=strategyType, provider=provider)
    if snapshot is None:
        raise api_error(404, "SCREENER_SNAPSHOT_NOT_FOUND", f"{trade_date.isoformat()} 选股快照不存在")
    return ok(screener_snapshot_payload(snapshot, db))


@router.get("/screeners/snapshots/{snapshot_id}/items/{item_id}")
def read_screener_item_detail(snapshot_id: str, item_id: str, db: Session = Depends(get_db)):
    item = get_screener_item(db, snapshot_id, item_id)
    if item is None:
        raise api_error(404, "SCREENER_ITEM_NOT_FOUND", "选股条目不存在")
    in_watchlist = db.query(m.WatchlistItem).filter(m.WatchlistItem.code == item.code).first() is not None
    try:
        payload = screener_item_detail_payload(item, in_watchlist=in_watchlist)
    except DailyBarError as exc:
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc
    return ok(payload)


@router.get("/screeners/stocks/{code}/daily-bars")
def read_stock_daily_bars(
    code: str,
    endDate: date | None = Query(None),
    lookback: int = Query(30, ge=1, le=120),
):
    try:
        bars = get_daily_bar_series(code, end_date=endDate, lookback=lookback)
    except DailyBarError as exc:
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc
    return ok(
        {
            "code": str(code).zfill(6),
            "endDate": (endDate or bars[-1].trade_date).isoformat(),
            "lookback": lookback,
            "priceAdjustment": "raw",
            "bars": [daily_bar_payload(bar) for bar in bars],
        }
    )
