from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import LimitUpBreakSnapshotCreate
from ..serializers import limit_up_break_snapshot_payload
from ..services.limit_up_breaks import LimitUpBreakError, generate_limit_up_break_snapshot, get_limit_up_break_snapshot
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
        raise api_error(exc.status_code, exc.code, exc.message) from exc
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
