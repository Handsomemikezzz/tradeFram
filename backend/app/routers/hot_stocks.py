from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import HotStockSnapshotCreate
from ..serializers_hot_stocks import hot_stock_latest_payload, hot_stock_summary_payload
from ..services.hot_stocks import HotStockError, get_latest_snapshot, get_or_create_today_snapshot
from ..utils import api_error, ok

router = APIRouter()


@router.post("/hot-stocks/snapshots")
def create_hot_stock_snapshot(payload: HotStockSnapshotCreate, db: Session = Depends(get_db)):
    try:
        snapshot, is_fallback, error_message = get_or_create_today_snapshot(
            db,
            limit=payload.limit,
            source=payload.source,
            force_refresh=payload.forceRefresh,
        )
    except HotStockError as exc:
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc
    if snapshot is None:
        raise api_error(404, "HOT_STOCK_SNAPSHOT_NOT_FOUND", "热门股数据暂时无法获取，无历史快照可回退")
    return ok(hot_stock_latest_payload(db, snapshot, is_fallback=is_fallback, error_message=error_message))


@router.get("/hot-stocks/latest")
def read_hot_stock_latest(
    source: str = Query("EastmoneyHotRank"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    snapshot, is_fallback, error_message = get_or_create_today_snapshot(
        db,
        limit=limit,
        source=source,
        force_refresh=False,
    )
    if snapshot is None:
        raise api_error(404, "HOT_STOCK_SNAPSHOT_NOT_FOUND", "热门股数据暂时无法获取，请稍后重试")
    return ok(hot_stock_latest_payload(db, snapshot, is_fallback=is_fallback, error_message=error_message))


@router.get("/hot-stocks/summary")
def read_hot_stock_summary(
    source: str = Query("EastmoneyHotRank"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    snapshot = get_latest_snapshot(db, source=source)
    error_message = "暂无热门股快照" if snapshot is None else None
    return ok(hot_stock_summary_payload(db, snapshot, limit=limit, error_message=error_message))
