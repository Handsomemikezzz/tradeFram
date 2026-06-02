from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from . import models as m
from .utils import dt_iso


def hot_stock_latest_payload(
    db: Session,
    snapshot: m.HotStockSnapshot,
    *,
    is_fallback: bool = False,
    error_message: str | None = None,
) -> dict:
    items = (
        db.query(m.HotStockItem)
        .filter(m.HotStockItem.snapshot_id == snapshot.id)
        .order_by(m.HotStockItem.rank)
        .all()
    )

    # Gather watchlist codes
    watchlist_codes = {
        row[0]
        for row in db.query(m.WatchlistItem.code).all()
    }

    # Gather open review card codes (nullable code)
    open_card_codes = {
        row[0]
        for row in db.query(m.StockReviewCard.code)
        .filter(m.StockReviewCard.status == "OPEN", m.StockReviewCard.code.isnot(None))
        .all()
    }

    # Gather research status per code
    research_map = _build_research_map(db, [item.code for item in items])

    return {
        "snapshotId": snapshot.id,
        "tradeDate": snapshot.trade_date.isoformat(),
        "source": snapshot.source,
        "status": snapshot.status,
        "isFallback": is_fallback,
        "errorMessage": error_message,
        "generatedAt": dt_iso(snapshot.created_at),
        "items": [
            _hot_stock_item_payload(
                item,
                in_watchlist=item.code in watchlist_codes,
                has_open_review_card=item.code in open_card_codes,
                research=research_map.get(item.code, {"status": "NONE"}),
            )
            for item in items
        ],
    }


def hot_stock_summary_payload(
    db: Session,
    snapshot: m.HotStockSnapshot | None,
    *,
    limit: int | None = None,
    error_message: str | None = None,
) -> dict:
    if snapshot is None:
        return {
            "items": [],
            "errorMessage": error_message or "暂无热门股快照",
        }
    query = (
        db.query(m.HotStockItem)
        .filter(m.HotStockItem.snapshot_id == snapshot.id)
        .order_by(m.HotStockItem.rank)
    )
    if limit is not None:
        query = query.limit(limit)
    items = query.all()
    return {
        "snapshotId": snapshot.id,
        "tradeDate": snapshot.trade_date.isoformat(),
        "source": snapshot.source,
        "items": [
            {
                "rank": item.rank,
                "code": item.code,
                "name": item.name,
                "trendLabel": item.trend_label,
            }
            for item in items
        ],
        "errorMessage": error_message,
    }


def _hot_stock_item_payload(
    item: m.HotStockItem,
    *,
    in_watchlist: bool,
    has_open_review_card: bool,
    research: dict,
) -> dict:
    return {
        "id": item.id,
        "rank": item.rank,
        "code": item.code,
        "name": item.name,
        "price": item.price,
        "changePercent": item.change_percent,
        "industry": item.industry,
        "ma5": item.ma5,
        "ma20": item.ma20,
        "trendLabel": item.trend_label,
        "isRecentLimitUpBreak": item.is_recent_limit_up_break,
        "inWatchlist": in_watchlist,
        "hasOpenReviewCard": has_open_review_card,
        "research": research,
    }


def _build_research_map(db: Session, codes: list[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not codes:
        return result

    # Check for completed reports
    reports = (
        db.query(m.ResearchReport)
        .filter(m.ResearchReport.code.in_(codes), m.ResearchReport.status == "COMPLETED")
        .order_by(desc(m.ResearchReport.generated_at))
        .all()
    )
    for report in reports:
        if report.code not in result:
            result[report.code] = {
                "status": "HAS_REPORT",
                "reportId": report.id,
            }

    # Check for running tasks
    tasks = (
        db.query(m.ResearchTask)
        .filter(
            m.ResearchTask.code.in_(codes),
            m.ResearchTask.status == "PROCESSING",
        )
        .all()
    )
    for task in tasks:
        if task.code not in result:
            result[task.code] = {
                "status": "RESEARCHING",
                "taskId": task.id,
            }

    return result
