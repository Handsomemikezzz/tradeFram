from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..serializers import log_payload, order_payload, risk_payload
from ..utils import ok

router = APIRouter()


@router.get("/orders")
def list_orders(
    keyword: str | None = None,
    code: str | None = None,
    status: str | None = None,
    side: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(m.PaperOrder).join(m.Stock)
    if code:
        query = query.filter(m.PaperOrder.code == code)
    if status:
        query = query.filter(m.PaperOrder.status == status)
    if side:
        query = query.filter(m.PaperOrder.side == side)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((m.PaperOrder.id.like(like)) | (m.PaperOrder.code.like(like)) | (m.Stock.name.like(like)))
    total = query.count()
    items = query.order_by(desc(m.PaperOrder.create_time)).offset((page - 1) * pageSize).limit(pageSize).all()
    return ok({"items": [order_payload(item) for item in items], "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})


@router.get("/risk-checks")
def list_risk_checks(
    keyword: str | None = None,
    code: str | None = None,
    passed: bool | None = None,
    rule: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(m.RiskCheck)
    if code:
        query = query.filter(m.RiskCheck.code == code)
    if passed is not None:
        query = query.filter(m.RiskCheck.passed.is_(passed))
    if rule:
        query = query.filter(m.RiskCheck.rule == rule)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((m.RiskCheck.code.like(like)) | (m.RiskCheck.id.like(like)) | (m.RiskCheck.reason.like(like)))
    total = query.count()
    items = query.order_by(desc(m.RiskCheck.checked_at)).offset((page - 1) * pageSize).limit(pageSize).all()
    return ok({"items": [risk_payload(item) for item in items], "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})


@router.get("/logs")
def list_logs(
    keyword: str | None = None,
    module: str | None = None,
    level: str | None = None,
    code: str | None = None,
    relId: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(m.SystemLog)
    if module:
        query = query.filter(m.SystemLog.module == module)
    if level:
        query = query.filter(m.SystemLog.level == level)
    if code:
        query = query.filter(m.SystemLog.code == code)
    if relId:
        query = query.filter(m.SystemLog.rel_id == relId)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((m.SystemLog.event.like(like)) | (m.SystemLog.detail.like(like)) | (m.SystemLog.module.like(like)))
    total = query.count()
    items = query.order_by(desc(m.SystemLog.time)).offset((page - 1) * pageSize).limit(pageSize).all()
    return ok({"items": [log_payload(item) for item in items], "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})
