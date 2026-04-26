from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import MonitoringCreate, MonitoringUpdate, WatchlistCreate
from ..services.research import require_stock
from ..utils import api_error, new_id


def add_watchlist_item(db: Session, payload: WatchlistCreate) -> m.WatchlistItem:
    stock = require_stock(db, payload.code)
    existing = db.query(m.WatchlistItem).filter(m.WatchlistItem.code == stock.code).first()
    if existing:
        raise api_error(409, "WATCHLIST_ALREADY_EXISTS", f"{stock.name} 已在观察池中", {"id": existing.id, "code": stock.code})
    item = m.WatchlistItem(
        id=new_id("wl"),
        code=stock.code,
        source=payload.source,
        report_id=payload.reportId,
        note=payload.note,
    )
    db.add(item)
    db.add(m.SystemLog(id=new_id("log"), level="INFO", module="Watchlist", code=stock.code, event="加入观察池", detail=f"{stock.name} 已加入观察池", rel_id=item.id))
    db.commit()
    db.refresh(item)
    return item


def add_monitoring_item(db: Session, payload: MonitoringCreate) -> m.MonitoringItem:
    stock = require_stock(db, payload.code)
    existing = db.query(m.MonitoringItem).filter(m.MonitoringItem.code == stock.code).first()
    if existing:
        raise api_error(409, "MONITORING_ITEM_ALREADY_EXISTS", f"{stock.name} 已在交易监控池中", {"id": existing.id, "code": stock.code})
    strategy_id = payload.strategyId or ("strategy_ma_breakout" if stock.code == "300750" else "strategy_ma_reversion")
    strategy_name = payload.strategyName or ("突破策略" if stock.code == "300750" else "均线回归")
    item = m.MonitoringItem(
        id=new_id("mon"),
        code=stock.code,
        enabled=payload.enabled,
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        strategy_params=payload.strategyParams,
        risk_params=payload.riskParams,
        source=payload.source,
        report_id=payload.reportId,
    )
    db.add(item)
    db.add(m.SystemLog(id=new_id("log"), level="INFO", module="Monitoring", code=stock.code, event="加入交易监控池", detail=f"{stock.name} 已加入模拟交易监控池", rel_id=item.id))
    db.commit()
    db.refresh(item)
    return item


def update_monitoring_item(db: Session, item_id: str, payload: MonitoringUpdate) -> m.MonitoringItem | None:
    item = db.get(m.MonitoringItem, item_id)
    if item is None:
        return None
    if payload.enabled is not None:
        item.enabled = payload.enabled
    item.updated_at = datetime.now(UTC)
    db.add(m.SystemLog(id=new_id("log"), level="INFO", module="Monitoring", code=item.code, event="更新监控项", detail=payload.reason or "用户更新监控项", rel_id=item.id))
    db.commit()
    db.refresh(item)
    return item
