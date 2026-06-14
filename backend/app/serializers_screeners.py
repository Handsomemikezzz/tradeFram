from __future__ import annotations

from sqlalchemy.orm import Session, object_session

from . import models as m
from .services.daily_bars import (
    PATTERN_A_DETAIL_LOOKBACK,
    build_markers_from_reason,
    daily_bar_payload,
    get_daily_bar_series,
)
from .utils import dt_iso


def screener_snapshot_payload(snapshot: m.ScreenerSnapshot, db: Session | None = None) -> dict:
    session = db or object_session(snapshot)
    items = []
    watchlist_codes: set[str] = set()
    if session is not None:
        items = (
            session.query(m.ScreenerItem)
            .filter(m.ScreenerItem.snapshot_id == snapshot.id)
            .order_by(m.ScreenerItem.status.asc(), m.ScreenerItem.score.desc(), m.ScreenerItem.code.asc())
            .all()
        )
        watchlist_codes = {row.code for row in session.query(m.WatchlistItem.code).all()}

    return {
        "id": snapshot.id,
        "tradeDate": snapshot.trade_date.isoformat(),
        "strategyType": snapshot.strategy_type,
        "strategyName": snapshot.strategy_name,
        "strategyVersion": snapshot.strategy_version,
        "provider": snapshot.provider,
        "priceAdjustment": snapshot.price_adjustment,
        "criteria": snapshot.criteria,
        "scanCount": snapshot.scan_count,
        "eligibleCount": snapshot.eligible_count,
        "confirmedCount": snapshot.confirmed_count,
        "pendingCount": snapshot.pending_count,
        "coverage": snapshot.coverage,
        "generatedAt": dt_iso(snapshot.generated_at),
        "updatedAt": dt_iso(snapshot.updated_at),
        "items": [screener_item_summary_payload(item, in_watchlist=item.code in watchlist_codes) for item in items],
    }


def screener_item_summary_payload(item: m.ScreenerItem, *, in_watchlist: bool) -> dict:
    reason = item.reason or {}
    regulatory = reason.get("regulatory") or {}
    trend = reason.get("trend") or {}
    volume = reason.get("volume") or {}

    # Calculate R:R metrics for Pattern A
    entry = None
    stop_loss = None
    target = None
    rr = None

    stabilization = reason.get("stabilization")
    confirm_bar = reason.get("confirmBar")
    if stabilization and confirm_bar:
        box_low = stabilization.get("boxLow")
        close_price = confirm_bar.get("close")
        if box_low is not None and close_price is not None:
            entry = round(close_price, 4)
            stop_loss = round(box_low, 4)
            target = round(entry + 2 * (entry - stop_loss), 4)
            diff = entry - stop_loss
            rr = round((target - entry) / diff, 2) if diff > 0 else 0.0

    return {
        "id": item.id,
        "snapshotId": item.snapshot_id,
        "tradeDate": item.trade_date.isoformat(),
        "code": item.code,
        "name": item.name,
        "industry": item.industry,
        "status": item.status,
        "signalDate": item.signal_date.isoformat(),
        "score": item.score,
        "priceActionScore": item.price_action_score,
        "movingAverageScore": item.moving_average_score,
        "volumeScore": item.volume_score,
        "changePercent": item.change_percent,
        "tags": item.tags,
        "inWatchlist": in_watchlist,
        # R:R Metrics
        "entry": entry,
        "stopLoss": stop_loss,
        "target": target,
        "rr": rr,
        # uptrend-specific (None for other strategies)
        "setupType": reason.get("setupType"),
        "setupLabel": reason.get("setupLabel"),
        "indexCode": regulatory.get("indexCode"),
        "indexName": regulatory.get("indexName"),
        "deviation3Percent": regulatory.get("deviation3Percent"),
        "deviation10Percent": regulatory.get("deviation10Percent"),
        "deviation30Percent": regulatory.get("deviation30Percent"),
        "distanceToMa10Percent": trend.get("distanceToMa10Percent"),
        "avgAmount20": volume.get("avgAmount20"),
        "avgAmount5": volume.get("avgAmount5"),
    }


def screener_item_detail_payload(item: m.ScreenerItem, *, in_watchlist: bool) -> dict:
    bars = get_daily_bar_series(item.code, end_date=item.trade_date, lookback=PATTERN_A_DETAIL_LOOKBACK)
    return {
        **screener_item_summary_payload(item, in_watchlist=in_watchlist),
        "reason": item.reason,
        "bars": [daily_bar_payload(bar) for bar in bars],
        "markers": build_markers_from_reason(item.reason),
    }
