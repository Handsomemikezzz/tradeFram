from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from .. import models as m
from ..data_layer.warehouse.reader import WarehouseInstrument, WarehouseMarketDataStore
from ..utils import new_id
from .pattern_a import (
    PATTERN_A_STRATEGY_NAME,
    PATTERN_A_STRATEGY_TYPE,
    PATTERN_A_STRATEGY_VERSION,
    PatternABar,
    PatternACandidate,
    SIGNAL_WINDOW_DAYS,
    evaluate_pattern_a,
)
from .stock_universe import (
    ensure_main_board_coverage,
    main_board_non_st_stocks,
    resolve_default_screener_trade_date,
    warehouse_bar_change_percent,
)

SCAN_LOOKBACK_TRADE_DAYS = 90
SUPPORTED_STRATEGIES = {PATTERN_A_STRATEGY_TYPE}


class ScreenerError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


@dataclass(frozen=True)
class ScanStats:
    scan_count: int
    eligible_count: int
    confirmed_count: int
    pending_count: int
    anomaly_filtered_count: int
    coverage: float


def generate_pattern_a_snapshot(
    db: Session,
    trade_date: date | None = None,
    *,
    provider: str = "AkShare",
) -> m.ScreenerSnapshot:
    provider = provider or "AkShare"
    target_date = trade_date or resolve_default_screener_trade_date()
    if target_date is None:
        raise ScreenerError("SCREENER_NO_PRICE_DATA", "无可用于选股的未复权日 K 数据", status_code=422)

    store = WarehouseMarketDataStore()
    stocks = main_board_non_st_stocks(store=store)
    if not stocks:
        raise ScreenerError("SCREENER_NO_PRICE_DATA", "缺少主板股票主数据", status_code=422)

    known_open_dates = store.open_trade_dates(end_date=target_date)
    trade_dates = store.trade_dates(end_date=target_date)
    if target_date not in known_open_dates and target_date not in trade_dates:
        raise ScreenerError(
            "SCREENER_NO_PRICE_DATA",
            f"{target_date.isoformat()} 无可用于选股的未复权日 K 数据",
            status_code=422,
        )

    ensure_main_board_coverage(target_date, stocks, provider=provider)

    stock_codes = {stock.code for stock in stocks}
    if target_date not in trade_dates:
        raise ScreenerError(
            "SCREENER_NO_PRICE_DATA",
            f"{target_date.isoformat()} 无可用于选股的未复权日 K 数据",
            status_code=422,
        )

    target_index = trade_dates.index(target_date)
    start_index = max(0, target_index - SCAN_LOOKBACK_TRADE_DAYS)
    start_date = trade_dates[start_index]
    bars_frame = store.daily_bars_frame(
        codes=stock_codes,
        start_date=start_date,
        end_date=target_date,
        columns=["code", "trade_date", "open", "high", "low", "close", "volume", "amount"],
    )
    if bars_frame.empty:
        raise ScreenerError("SCREENER_NO_PRICE_DATA", f"{target_date.isoformat()} 无可用于选股的未复权日 K 数据", status_code=422)

    bars_by_code = _bars_by_code(bars_frame)
    instruments = {stock.code: stock for stock in stocks}

    scan_count = len(stocks)
    eligible_count = 0
    anomaly_filtered_count = 0
    candidates: list[tuple[WarehouseInstrument, PatternACandidate]] = []

    for stock in stocks:
        bars = bars_by_code.get(stock.code, [])
        if len(bars) < 60:
            continue
        eligible_count += 1
        pattern_bars = _to_pattern_bars(bars)
        if _has_window_ex_rights(pattern_bars, target_date):
            anomaly_filtered_count += 1
            continue
        result = evaluate_pattern_a(pattern_bars, target_date)
        if result is not None:
            candidates.append((instruments[stock.code], result))

    candidates.sort(
        key=lambda item: (
            0 if item[1].status == "CONFIRMED" else 1,
            -item[1].score,
            item[0].code,
        )
    )

    confirmed_count = sum(1 for _, item in candidates if item.status == "CONFIRMED")
    pending_count = len(candidates) - confirmed_count
    _, expected, coverage = _coverage_from_frame(target_date, stocks, bars_frame)

    stats = ScanStats(
        scan_count=scan_count,
        eligible_count=eligible_count,
        confirmed_count=confirmed_count,
        pending_count=pending_count,
        anomaly_filtered_count=anomaly_filtered_count,
        coverage=round(coverage, 4),
    )

    return _persist_snapshot(db, target_date, provider, candidates, stats)


def get_screener_snapshot(
    db: Session,
    trade_date: date,
    *,
    strategy_type: str = PATTERN_A_STRATEGY_TYPE,
    provider: str = "AkShare",
) -> m.ScreenerSnapshot | None:
    return (
        db.query(m.ScreenerSnapshot)
        .filter(
            m.ScreenerSnapshot.trade_date == trade_date,
            m.ScreenerSnapshot.strategy_type == strategy_type,
            m.ScreenerSnapshot.strategy_version == PATTERN_A_STRATEGY_VERSION,
            m.ScreenerSnapshot.provider == provider,
        )
        .first()
    )


def get_default_screener_snapshot(
    db: Session,
    *,
    strategy_type: str = PATTERN_A_STRATEGY_TYPE,
    provider: str = "AkShare",
) -> tuple[m.ScreenerSnapshot | None, date | None]:
    target_date = resolve_default_screener_trade_date()
    if target_date is None:
        return None, None
    snapshot = get_screener_snapshot(db, target_date, strategy_type=strategy_type, provider=provider)
    return snapshot, target_date


def get_screener_item(db: Session, snapshot_id: str, item_id: str) -> m.ScreenerItem | None:
    return (
        db.query(m.ScreenerItem)
        .filter(m.ScreenerItem.snapshot_id == snapshot_id, m.ScreenerItem.id == item_id)
        .first()
    )


def _persist_snapshot(
    db: Session,
    trade_date: date,
    provider: str,
    candidates: list[tuple[WarehouseInstrument, PatternACandidate]],
    stats: ScanStats,
) -> m.ScreenerSnapshot:
    snapshot = (
        db.query(m.ScreenerSnapshot)
        .filter(
            m.ScreenerSnapshot.trade_date == trade_date,
            m.ScreenerSnapshot.strategy_type == PATTERN_A_STRATEGY_TYPE,
            m.ScreenerSnapshot.strategy_version == PATTERN_A_STRATEGY_VERSION,
            m.ScreenerSnapshot.provider == provider,
        )
        .first()
    )
    now = datetime.now(UTC)
    criteria = {
        "strategyType": PATTERN_A_STRATEGY_TYPE,
        "strategyVersion": PATTERN_A_STRATEGY_VERSION,
        "signalWindowDays": SIGNAL_WINDOW_DAYS,
        "anomalyFilteredCount": stats.anomaly_filtered_count,
    }
    if snapshot is None:
        snapshot = m.ScreenerSnapshot(
            id=new_id("scr"),
            trade_date=trade_date,
            strategy_type=PATTERN_A_STRATEGY_TYPE,
            strategy_name=PATTERN_A_STRATEGY_NAME,
            strategy_version=PATTERN_A_STRATEGY_VERSION,
            provider=provider,
            price_adjustment="raw",
            criteria=criteria,
            generated_at=now,
            updated_at=now,
        )
        db.add(snapshot)
    else:
        snapshot.criteria = criteria
        snapshot.updated_at = now

    db.query(m.ScreenerItem).filter(m.ScreenerItem.snapshot_id == snapshot.id).delete(synchronize_session=False)

    snapshot.scan_count = stats.scan_count
    snapshot.eligible_count = stats.eligible_count
    snapshot.confirmed_count = stats.confirmed_count
    snapshot.pending_count = stats.pending_count
    snapshot.coverage = stats.coverage
    snapshot.generated_at = now

    for instrument, candidate in candidates:
        db.add(
            m.ScreenerItem(
                id=new_id("sci"),
                snapshot_id=snapshot.id,
                trade_date=trade_date,
                code=instrument.code,
                name=instrument.name,
                industry=instrument.industry or "未知",
                status=candidate.status,
                signal_date=candidate.signal_date,
                score=candidate.score,
                price_action_score=candidate.price_action_score,
                moving_average_score=candidate.moving_average_score,
                volume_score=candidate.volume_score,
                change_percent=candidate.change_percent,
                tags=candidate.tags,
                reason=candidate.reason,
            )
        )

    db.flush()
    return snapshot


def _bars_by_code(bars_frame) -> dict[str, list[PatternABar]]:
    grouped: dict[str, list[PatternABar]] = {}
    columns = ["code", "trade_date", "open", "high", "low", "close", "volume", "amount"]
    for row in bars_frame[columns].itertuples(index=False):
        code = str(row.code).zfill(6)
        grouped.setdefault(code, []).append(
            PatternABar(
                trade_date=row.trade_date,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=int(row.volume),
                amount=float(row.amount),
                change_percent=None,
            )
        )
    for code, bars in grouped.items():
        bars.sort(key=lambda bar: bar.trade_date)
        enriched: list[PatternABar] = []
        for index, bar in enumerate(bars):
            previous_close = bars[index - 1].close if index > 0 else None
            enriched.append(
                PatternABar(
                    trade_date=bar.trade_date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    amount=bar.amount,
                    change_percent=warehouse_bar_change_percent_from_values(bar.close, previous_close),
                )
            )
        grouped[code] = enriched
    return grouped


def warehouse_bar_change_percent_from_values(close: float, previous_close: float | None) -> float | None:
    if previous_close is None or not previous_close:
        return None
    return round(((close - previous_close) / previous_close) * 100, 2)


def _to_pattern_bars(bars: list[PatternABar]) -> list[PatternABar]:
    return bars


def _has_window_ex_rights(bars: list[PatternABar], target_date: date) -> bool:
    window = [bar for bar in bars if bar.trade_date <= target_date][-SIGNAL_WINDOW_DAYS:]
    from .pattern_a import has_suspected_ex_rights

    return has_suspected_ex_rights(window)


def _coverage_from_frame(target_date: date, stocks: list[WarehouseInstrument], bars_frame) -> tuple[int, int, float]:
    expected = len(stocks)
    if expected == 0:
        return 0, 0, 0.0
    target_frame = bars_frame[bars_frame["trade_date"] == target_date]
    available = int(target_frame["code"].nunique()) if not target_frame.empty else 0
    return available, expected, available / expected
