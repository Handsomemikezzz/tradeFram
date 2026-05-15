from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import LimitUpBreakSnapshotCreate
from ..serializers import limit_up_break_snapshot_payload
from ..services.limit_up_breaks import LimitUpBreakError, generate_limit_up_break_snapshot, get_default_limit_up_break_snapshot, get_limit_up_break_snapshot, get_post_break_bars
from ..utils import api_error, ok

router = APIRouter()


@router.post("/limit-up-breaks/snapshots")
def create_limit_up_break_snapshot(payload: LimitUpBreakSnapshotCreate, db: Session = Depends(get_db)):
    try:
        snapshot = generate_limit_up_break_snapshot(db, payload.tradeDate, threshold=payload.threshold, provider=payload.provider)
        db.commit()
        db.refresh(snapshot)
    except LimitUpBreakError as exc:
        db.rollback()
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc
    return ok(limit_up_break_snapshot_payload(snapshot))


@router.get("/limit-up-breaks/snapshots/default/latest")
def read_default_limit_up_break_snapshot(
    threshold: int = Query(2, ge=1),
    provider: str = Query("AkShare"),
    db: Session = Depends(get_db),
):
    snapshot, target_date = get_default_limit_up_break_snapshot(db, threshold=threshold, provider=provider)
    if target_date is None:
        raise api_error(404, "LIMIT_UP_BREAK_SNAPSHOT_NOT_FOUND", "无默认断板快照日期")
    if snapshot is None:
        raise api_error(404, "LIMIT_UP_BREAK_SNAPSHOT_NOT_FOUND", f"{target_date.isoformat()} 断板快照不存在")
    return ok(limit_up_break_snapshot_payload(snapshot))


@router.get("/limit-up-breaks/snapshots/{trade_date}")
def read_limit_up_break_snapshot(
    trade_date: date,
    threshold: int = Query(2, ge=1),
    provider: str = Query("AkShare"),
    db: Session = Depends(get_db),
):
    snapshot = get_limit_up_break_snapshot(db, trade_date, threshold=threshold, provider=provider)
    if snapshot is None:
        raise api_error(404, "LIMIT_UP_BREAK_SNAPSHOT_NOT_FOUND", f"{trade_date.isoformat()} 断板快照不存在")
    return ok(limit_up_break_snapshot_payload(snapshot))


@router.get("/limit-up-breaks/stocks/{code}/post-break-bars")
def read_post_break_bars(
    code: str,
    breakDate: date = Query(...),
    maxForwardDays: int = Query(5, ge=0, le=20),
    adjustment: str = Query("none"),
):
    try:
        bars = get_post_break_bars(code, breakDate, max_forward_days=maxForwardDays, price_adjustment=adjustment)
    except LimitUpBreakError as exc:
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc
    return ok(
        {
            "code": str(code).zfill(6),
            "breakDate": breakDate.isoformat(),
            "priceAdjustment": "none",
            "bars": [
                {
                    "tradeDate": bar.trade_date.isoformat(),
                    "close": bar.close,
                    "changePercent": bar.change_percent,
                    "dayOffset": bar.day_offset,
                }
                for bar in bars
            ],
        }
    )
