from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..schemas import MonitoringCreate, MonitoringUpdate, WatchlistCreate
from ..serializers import monitoring_payload, watchlist_payload
from ..services.monitoring import add_monitoring_item, add_watchlist_item, update_monitoring_item
from ..utils import api_error, ok

router = APIRouter()


@router.post("/watchlist/items")
def create_watchlist_item(payload: WatchlistCreate, db: Session = Depends(get_db)):
    item = add_watchlist_item(db, payload)
    return ok(watchlist_payload(item))


@router.get("/monitoring-pool/items")
def list_monitoring_items(
    enabled: bool | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(m.MonitoringItem).join(m.Stock)
    if enabled is not None:
        query = query.filter(m.MonitoringItem.enabled.is_(enabled))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((m.MonitoringItem.code.like(like)) | (m.Stock.name.like(like)))
    total = query.count()
    items = query.order_by(desc(m.MonitoringItem.created_at)).offset((page - 1) * pageSize).limit(pageSize).all()
    response_items = []
    for item in items:
        latest_signal = db.query(m.Signal).filter(m.Signal.monitoring_item_id == item.id).order_by(desc(m.Signal.generated_at)).first()
        latest_risk = db.query(m.RiskCheck).filter(m.RiskCheck.code == item.code).order_by(desc(m.RiskCheck.checked_at)).first()
        latest_order = db.query(m.PaperOrder).filter(m.PaperOrder.code == item.code).order_by(desc(m.PaperOrder.create_time)).first()
        response_items.append(monitoring_payload(item, latest_signal, latest_risk, latest_order))
    return ok({"items": response_items, "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})


@router.post("/monitoring-pool/items")
def create_monitoring_item(payload: MonitoringCreate, db: Session = Depends(get_db)):
    item = add_monitoring_item(db, payload)
    return ok(monitoring_payload(item))


@router.patch("/monitoring-pool/items/{id}")
def patch_monitoring_item(id: str, payload: MonitoringUpdate, db: Session = Depends(get_db)):
    item = update_monitoring_item(db, id, payload)
    if item is None:
        raise api_error(404, "MONITORING_ITEM_NOT_FOUND", f"监控项 {id} 不存在")
    return ok(monitoring_payload(item))
