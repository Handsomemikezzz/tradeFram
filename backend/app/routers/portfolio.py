from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..serializers import position_payload
from ..utils import dt_iso, ok

router = APIRouter()


@router.get("/portfolio/account-summary")
def account_summary(db: Session = Depends(get_db)):
    account = db.get(m.PaperAccount, "paper_default")
    if account is None:
        account = m.PaperAccount(id="paper_default", initial_cash=1_000_000, cash=1_000_000)
        db.add(account)
        db.commit()
        db.refresh(account)
    positions = db.query(m.Position).filter(m.Position.account_id == account.id).all()
    position_market_value = sum(p.market_value for p in positions)
    total_assets = account.cash + position_market_value
    today_pnl = sum(p.unrealized_pnl for p in positions)
    position_ratio = (position_market_value / total_assets * 100) if total_assets else 0
    return ok(
        {
            "accountId": account.id,
            "currency": account.currency,
            "totalAssets": round(total_assets, 2),
            "availableCash": round(account.cash, 2),
            "positionMarketValue": round(position_market_value, 2),
            "todayPnl": round(today_pnl, 2),
            "todayPnlPct": round(today_pnl / account.initial_cash * 100, 2) if account.initial_cash else 0,
            "positionRatio": round(position_ratio, 2),
            "updateTime": dt_iso(account.updated_at),
        }
    )


@router.get("/portfolio/positions")
def list_positions(
    keyword: str | None = None,
    code: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(m.Position).join(m.Stock)
    if code:
        query = query.filter(m.Position.code == code)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((m.Position.code.like(like)) | (m.Stock.name.like(like)))
    total = query.count()
    items = query.offset((page - 1) * pageSize).limit(pageSize).all()
    return ok({"items": [position_payload(item) for item in items], "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})
