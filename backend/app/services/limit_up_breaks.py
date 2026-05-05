from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models as m
from ..data_layer.warehouse.reader import WarehouseInstrument, WarehouseMarketDataStore, WarehousePriceBar
from ..utils import new_id


class LimitUpBreakError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def calculate_limit_up_price(previous_close: float) -> float:
    value = (Decimal(str(previous_close)) * Decimal("1.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(value)


def generate_limit_up_break_snapshot(db: Session, trade_date: date | None = None, *, threshold: int = 2, provider: str = "AkShare") -> m.LimitUpBreakSnapshot:
    if threshold < 1:
        raise LimitUpBreakError("INVALID_THRESHOLD", "连板起步门槛必须大于等于 1")
    provider = provider or "AkShare"
    target_date = _resolve_snapshot_trade_date(trade_date, provider)
    if target_date is None:
        raise LimitUpBreakError("NO_PRICE_DATA", "无可用于断板监控的未复权日 K 数据", status_code=422)

    trade_dates = _known_trade_dates(db, provider, target_date)
    previous_trade_date = _previous_trade_date(trade_dates, target_date)
    if previous_trade_date is None:
        raise LimitUpBreakError("INSUFFICIENT_HISTORY", f"{target_date.isoformat()} 缺少上一交易日行情", status_code=422)

    candidates: list[tuple[WarehouseInstrument, int]] = []
    for stock in _main_board_non_st_stocks(db):
        height = _limit_up_height_ending_on(db, stock.code, previous_trade_date, trade_dates, provider)
        if height >= threshold:
            candidates.append((stock, height))

    snapshot = _upsert_snapshot(db, target_date, previous_trade_date, threshold, provider)
    db.query(m.LimitUpBreakItem).filter(m.LimitUpBreakItem.snapshot_id == snapshot.id).delete(synchronize_session=False)

    break_items: list[m.LimitUpBreakItem] = []
    for stock, height in candidates:
        today_bar = _bar_for(db, stock.code, target_date, provider)
        previous_bar = _bar_for(db, stock.code, previous_trade_date, provider)
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


def _main_board_non_st_stocks(db: Session) -> list[WarehouseInstrument]:
    stocks = WarehouseMarketDataStore().list_instruments()
    return [stock for stock in stocks if stock.status.lower() == "active" and _is_main_board(stock) and not _is_st(stock)]


def _is_main_board(stock: WarehouseInstrument) -> bool:
    if stock.exchange == "SH":
        return stock.code.startswith(("600", "601", "603", "605"))
    if stock.exchange == "SZ":
        return stock.code.startswith(("000", "001", "002", "003"))
    return False


def _is_st(stock: WarehouseInstrument) -> bool:
    normalized = stock.name.upper().replace(" ", "")
    return normalized.startswith(("*ST", "ST", "S*ST"))


def _known_trade_dates(db: Session, provider: str, end_date: date) -> list[date]:
    return WarehouseMarketDataStore().trade_dates(end_date=end_date)


def _latest_trade_date(db: Session, provider: str) -> date | None:
    return WarehouseMarketDataStore().latest_trade_date()


def _resolve_snapshot_trade_date(requested: date | None, provider: str) -> date | None:
    store = WarehouseMarketDataStore()
    if requested is None:
        return store.latest_trade_date()
    dates = store.trade_dates(end_date=requested)
    return dates[-1] if dates else None


def _previous_trade_date(trade_dates: list[date], target_date: date) -> date | None:
    previous = [day for day in trade_dates if day < target_date]
    return previous[-1] if previous else None


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


def _is_limit_up(close: float, previous_close: float) -> bool:
    return Decimal(str(close)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal(str(calculate_limit_up_price(previous_close))).quantize(Decimal("0.01"))


def _bar_for(db: Session, code: str, trade_date: date, provider: str) -> WarehousePriceBar | None:
    return WarehouseMarketDataStore().get_bar(code, trade_date)
