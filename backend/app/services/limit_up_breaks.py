from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models as m
from ..data_layer.warehouse.reader import WarehouseInstrument, WarehouseMarketDataStore, WarehousePriceBar
from ..utils import CN_TZ, new_id
from .stock_universe import (
    main_board_non_st_stocks,
    resolve_default_screener_trade_date as resolve_default_limit_up_break_trade_date_impl,
)

MIN_TARGET_COVERAGE = 0.995
DEFAULT_READY_AFTER = time(18, 0)
SNAPSHOT_LOOKBACK_TRADE_DAYS = 90


@dataclass(frozen=True)
class _CachedPriceBar:
    close: float
    amount: float


@dataclass(frozen=True)
class PostBreakBar:
    trade_date: date
    close: float
    change_percent: float | None
    day_offset: int


class LimitUpBreakError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def calculate_limit_up_price(previous_close: float) -> float:
    value = (Decimal(str(previous_close)) * Decimal("1.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(value)


def resolve_default_limit_up_break_trade_date(*, now: datetime | None = None, provider: str = "AkShare") -> date | None:
    _ = provider
    return resolve_default_limit_up_break_trade_date_impl(now=now)


def generate_limit_up_break_snapshot(db: Session, trade_date: date | None = None, *, threshold: int = 2, provider: str = "AkShare") -> m.LimitUpBreakSnapshot:
    if threshold < 1:
        raise LimitUpBreakError("INVALID_THRESHOLD", "连板起步门槛必须大于等于 1")
    provider = provider or "AkShare"
    target_date = _resolve_snapshot_trade_date(trade_date, provider)
    if target_date is None:
        raise LimitUpBreakError("NO_PRICE_DATA", "无可用于断板监控的未复权日 K 数据", status_code=422)

    store = WarehouseMarketDataStore()
    stocks = main_board_non_st_stocks(db, store=store)
    stock_codes = {stock.code for stock in stocks} if stocks else None
    known_open_dates = store.open_trade_dates(end_date=target_date)
    if target_date in known_open_dates:
        trade_dates, bars_frame = _load_snapshot_bars_with_calendar(store, stock_codes, target_date, known_open_dates)
    else:
        bars_frame = store.daily_bars_frame(codes=stock_codes, end_date=target_date, columns=["code", "trade_date", "close", "amount"])
        trade_dates = sorted(bars_frame["trade_date"].dropna().unique().tolist()) if not bars_frame.empty else []
    if bars_frame.empty:
        raise LimitUpBreakError("NO_PRICE_DATA", f"{target_date.isoformat()} 无可用于断板监控的未复权日 K 数据", status_code=422)
    if target_date not in trade_dates:
        raise LimitUpBreakError("NO_PRICE_DATA", f"{target_date.isoformat()} 无可用于断板监控的未复权日 K 数据", status_code=422)
    previous_trade_date = _previous_trade_date(trade_dates, target_date)
    if previous_trade_date is None:
        raise LimitUpBreakError("INSUFFICIENT_HISTORY", f"{target_date.isoformat()} 缺少上一交易日行情", status_code=422)

    _ensure_target_date_coverage_from_frame(target_date, stocks, bars_frame, provider)
    bars_by_code = _daily_bars_by_code(bars_frame)

    candidates: list[tuple[WarehouseInstrument, int]] = []
    for stock in stocks:
        height, _ = _limit_up_height_ending_on_cached(stock.code, previous_trade_date, trade_dates, bars_by_code)
        if height >= threshold:
            candidates.append((stock, height))

    snapshot = _upsert_snapshot(db, target_date, previous_trade_date, threshold, provider)
    db.query(m.LimitUpBreakItem).filter(m.LimitUpBreakItem.snapshot_id == snapshot.id).delete(synchronize_session=False)

    break_items: list[m.LimitUpBreakItem] = []
    for stock, height in candidates:
        today_bar = _cached_bar_for(bars_by_code, stock.code, target_date)
        previous_bar = _cached_bar_for(bars_by_code, stock.code, previous_trade_date)
        if today_bar is None:
            break_items.append(_new_item(snapshot, stock, height, None, None, "SUSPENDED"))
            continue
        if previous_bar is not None and _is_limit_up(today_bar.close, previous_bar.close):
            continue
        change_percent = round(((today_bar.close - previous_bar.close) / previous_bar.close) * 100, 2) if previous_bar and previous_bar.close else None
        break_items.append(_new_item(snapshot, stock, height, change_percent, today_bar.amount, "CLOSE_NOT_LIMIT_UP"))

    for item in break_items:
        db.add(item)
    snapshot.candidate_count = len(candidates)
    snapshot.break_count = len(break_items)
    snapshot.suspended_break_count = sum(1 for item in break_items if item.break_type == "SUSPENDED")
    snapshot.updated_at = datetime.now(UTC)
    db.flush()
    return snapshot


def get_limit_up_break_snapshot(db: Session, trade_date: date, *, threshold: int = 2, provider: str = "AkShare") -> m.LimitUpBreakSnapshot | None:
    target_date = _resolve_snapshot_trade_date(trade_date, provider)
    if target_date is None:
        return None
    return (
        db.query(m.LimitUpBreakSnapshot)
        .filter(
            m.LimitUpBreakSnapshot.trade_date == target_date,
            m.LimitUpBreakSnapshot.threshold == threshold,
            func.lower(m.LimitUpBreakSnapshot.data_source) == provider.lower(),
        )
        .first()
    )


def get_default_limit_up_break_snapshot(db: Session, *, threshold: int = 2, provider: str = "AkShare") -> tuple[m.LimitUpBreakSnapshot | None, date | None]:
    target_date = resolve_default_limit_up_break_trade_date(provider=provider)
    if target_date is None:
        return None, None
    return get_limit_up_break_snapshot(db, target_date, threshold=threshold, provider=provider), target_date


def get_post_break_bars(
    code: str,
    break_date: date,
    *,
    max_forward_days: int = 5,
    price_adjustment: str = "raw",
) -> list[PostBreakBar]:
    if max_forward_days < 0:
        raise LimitUpBreakError("INVALID_FORWARD_DAYS", "后续交易日数量不能小于 0")
    if price_adjustment.lower() not in {"raw", "none"}:
        raise LimitUpBreakError("INVALID_PRICE_ADJUSTMENT", "断板后走势仅支持未复权日 K", status_code=422)

    normalized_code = str(code).zfill(6)
    store = WarehouseMarketDataStore()
    trade_dates = _post_break_trade_dates(store, break_date, max_forward_days)
    if not trade_dates:
        raise LimitUpBreakError("NO_PRICE_DATA", f"{break_date.isoformat()} 起无可用于走势展示的交易日", status_code=404)

    previous_date = _previous_trade_date(store.open_trade_dates(end_date=break_date), break_date)
    load_start = previous_date or trade_dates[0]
    raw_bars = store.get_daily_bars(
        normalized_code,
        start_date=load_start,
        end_date=trade_dates[-1],
        price_adjustment="raw",
    )
    bars_by_date = {bar.trade_date: bar for bar in raw_bars}
    result: list[PostBreakBar] = []
    for offset, trade_date in enumerate(trade_dates):
        bar = bars_by_date.get(trade_date)
        if bar is None:
            continue
        previous_bar = bars_by_date.get(trade_dates[offset - 1] if offset > 0 else previous_date)
        change_percent = round(((bar.close - previous_bar.close) / previous_bar.close) * 100, 2) if previous_bar and previous_bar.close else None
        result.append(
            PostBreakBar(
                trade_date=trade_date,
                close=round(bar.close, 2),
                change_percent=change_percent,
                day_offset=offset,
            )
        )
    return result


def _upsert_snapshot(db: Session, trade_date: date, previous_trade_date: date, threshold: int, provider: str) -> m.LimitUpBreakSnapshot:
    snapshot = get_limit_up_break_snapshot(db, trade_date, threshold=threshold, provider=provider)
    if snapshot is None:
        snapshot = m.LimitUpBreakSnapshot(
            id=new_id("lub"),
            trade_date=trade_date,
            previous_trade_date=previous_trade_date,
            threshold=threshold,
            data_source=provider,
            price_adjustment="none",
        )
        db.add(snapshot)
        db.flush()
    else:
        snapshot.previous_trade_date = previous_trade_date
        snapshot.price_adjustment = "none"
    return snapshot


def _new_item(
    snapshot: m.LimitUpBreakSnapshot,
    stock: WarehouseInstrument,
    height: int,
    change_percent: float | None,
    amount: float | None,
    break_type: str,
) -> m.LimitUpBreakItem:
    return m.LimitUpBreakItem(
        id=new_id("lubi"),
        snapshot_id=snapshot.id,
        trade_date=snapshot.trade_date,
        code=stock.code,
        name=stock.name,
        previous_limit_up_height=height,
        change_percent=change_percent,
        amount=amount,
        intraday_break=None,
        break_type=break_type,
    )


def _ensure_target_date_coverage(db: Session, target_date: date, provider: str) -> None:
    stocks = main_board_non_st_stocks(db)
    available, expected, coverage = _target_date_coverage(target_date, stocks)
    if expected < 5:
        return
    if coverage < MIN_TARGET_COVERAGE:
        raise LimitUpBreakError(
            "DATA_COVERAGE_TOO_LOW",
            f"{target_date.isoformat()} 未复权日 K 行情覆盖不足，可能是数据同步失败；请先补齐行情后再生成断板监控。",
            status_code=422,
            details={
                "tradeDate": target_date.isoformat(),
                "availableBars": available,
                "expectedBars": expected,
                "coverage": round(coverage, 4),
                "provider": provider,
            },
        )


def _target_date_coverage(target_date: date, stocks: list[WarehouseInstrument]) -> tuple[int, int, float]:
    expected = len(stocks)
    if expected == 0:
        return 0, 0, 0
    counts = WarehouseMarketDataStore().daily_bar_counts_by_date(codes={stock.code for stock in stocks}, end_date=target_date)
    available = counts.get(target_date, 0)
    return available, expected, available / expected


def _load_snapshot_bars_with_calendar(
    store: WarehouseMarketDataStore,
    stock_codes: set[str] | None,
    target_date: date,
    known_open_dates: list[date],
) -> tuple[list[date], object]:
    target_index = known_open_dates.index(target_date)
    start_index = max(0, target_index - SNAPSHOT_LOOKBACK_TRADE_DAYS)
    force_full_history = False
    while True:
        calendar_dates = known_open_dates[start_index : target_index + 1]
        start_date = None if force_full_history or len(known_open_dates) < 5 else calendar_dates[0]
        bars_frame = store.daily_bars_frame(
            codes=stock_codes,
            start_date=start_date,
            end_date=target_date,
            columns=["code", "trade_date", "close", "amount"],
        )
        frame_dates = sorted(bars_frame["trade_date"].dropna().unique().tolist()) if not bars_frame.empty else []
        trade_dates = sorted(set(calendar_dates) | set(frame_dates))
        if bars_frame.empty:
            return trade_dates, bars_frame
        bars_by_code = _daily_bars_by_code(bars_frame)
        may_be_truncated = start_date is not None
        has_truncated_height = False
        previous_trade_date = trade_dates[-2] if len(trade_dates) >= 2 else None
        if previous_trade_date is not None and may_be_truncated:
            for code in stock_codes or set(bars_by_code):
                _, truncated = _limit_up_height_ending_on_cached(code, previous_trade_date, trade_dates, bars_by_code)
                if truncated:
                    has_truncated_height = True
                    break
        if not has_truncated_height or start_index == 0:
            if has_truncated_height and start_index == 0 and not force_full_history:
                force_full_history = True
                continue
            return trade_dates, bars_frame
        start_index = max(0, start_index - SNAPSHOT_LOOKBACK_TRADE_DAYS)


def _ensure_target_date_coverage_from_frame(target_date: date, stocks: list[WarehouseInstrument], bars_frame, provider: str) -> None:
    expected = len(stocks)
    if expected < 5:
        return
    target_frame = bars_frame[bars_frame["trade_date"] == target_date]
    available = int(target_frame["code"].nunique()) if not target_frame.empty else 0
    coverage = available / expected if expected else 0
    if coverage < MIN_TARGET_COVERAGE:
        raise LimitUpBreakError(
            "DATA_COVERAGE_TOO_LOW",
            f"{target_date.isoformat()} 未复权日 K 行情覆盖不足，可能是数据同步失败；请先补齐行情后再生成断板监控。",
            status_code=422,
            details={
                "tradeDate": target_date.isoformat(),
                "availableBars": available,
                "expectedBars": expected,
                "coverage": round(coverage, 4),
                "provider": provider,
            },
        )


def _latest_covered_trade_date(end_date: date | None, provider: str, *, min_coverage: float = MIN_TARGET_COVERAGE) -> date | None:
    stocks = main_board_non_st_stocks()
    counts = WarehouseMarketDataStore().daily_bar_counts_by_date(
        codes={stock.code for stock in stocks} if stocks else None,
        end_date=end_date,
    )
    if not counts:
        return None
    expected = len(stocks)
    for trade_date in sorted(counts, reverse=True):
        if expected < 5 or counts[trade_date] / expected >= min_coverage:
            return trade_date
    return None


def _known_trade_dates(db: Session, provider: str, end_date: date) -> list[date]:
    return WarehouseMarketDataStore().trade_dates(end_date=end_date)


def _latest_trade_date(db: Session, provider: str) -> date | None:
    return WarehouseMarketDataStore().latest_trade_date()


def _resolve_snapshot_trade_date(requested: date | None, provider: str) -> date | None:
    if requested is None:
        return resolve_default_limit_up_break_trade_date(provider=provider)
    return requested


def _previous_trade_date(trade_dates: list[date], target_date: date) -> date | None:
    previous = [day for day in trade_dates if day < target_date]
    return previous[-1] if previous else None


def _post_break_trade_dates(store: WarehouseMarketDataStore, break_date: date, max_forward_days: int) -> list[date]:
    # Use trading calendar only. Do not call store.trade_dates() — it scans the full daily_bars warehouse.
    trade_dates = store.open_trade_dates()
    if break_date not in trade_dates:
        trade_dates = sorted({*trade_dates, break_date})
    start_index = trade_dates.index(break_date)
    return trade_dates[start_index : start_index + max_forward_days + 1]


def _limit_up_height_ending_on(db: Session, code: str, target_date: date, trade_dates: list[date], provider: str) -> int:
    height = 0
    by_date = {day: index for index, day in enumerate(trade_dates)}
    index = by_date.get(target_date)
    if index is None:
        return 0
    while index > 0:
        current_day = trade_dates[index]
        previous_day = trade_dates[index - 1]
        current_bar = _bar_for(db, code, current_day, provider)
        previous_bar = _bar_for(db, code, previous_day, provider)
        if current_bar is None or previous_bar is None or not _is_limit_up(current_bar.close, previous_bar.close):
            break
        height += 1
        index -= 1
    return height


def _daily_bars_by_code(bars_frame) -> dict[str, dict[date, _CachedPriceBar]]:
    bars: dict[str, dict[date, _CachedPriceBar]] = {}
    columns = ["code", "trade_date", "close", "amount"]
    for row in bars_frame[columns].itertuples(index=False):
        code = str(row.code).zfill(6)
        bars.setdefault(code, {})[row.trade_date] = _CachedPriceBar(close=float(row.close), amount=float(row.amount))
    return bars


def _cached_bar_for(bars_by_code: dict[str, dict[date, _CachedPriceBar]], code: str, trade_date: date) -> _CachedPriceBar | None:
    return bars_by_code.get(str(code).zfill(6), {}).get(trade_date)


def _limit_up_height_ending_on_cached(code: str, target_date: date, trade_dates: list[date], bars_by_code: dict[str, dict[date, _CachedPriceBar]]) -> tuple[int, bool]:
    height = 0
    by_date = {day: index for index, day in enumerate(trade_dates)}
    index = by_date.get(target_date)
    if index is None:
        return 0, False
    while index > 0:
        current_day = trade_dates[index]
        previous_day = trade_dates[index - 1]
        current_bar = _cached_bar_for(bars_by_code, code, current_day)
        previous_bar = _cached_bar_for(bars_by_code, code, previous_day)
        if current_bar is None or previous_bar is None or not _is_limit_up(current_bar.close, previous_bar.close):
            break
        height += 1
        index -= 1
    return height, height > 0 and index == 0


def _is_limit_up(close: float, previous_close: float) -> bool:
    return Decimal(str(close)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal(str(calculate_limit_up_price(previous_close))).quantize(Decimal("0.01"))


def _bar_for(db: Session, code: str, trade_date: date, provider: str) -> WarehousePriceBar | None:
    return WarehouseMarketDataStore().get_bar(code, trade_date)
