from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from .. import models as m
from ..data_layer.warehouse.reader import WarehouseInstrument, WarehouseMarketDataStore, WarehousePriceBar
from ..utils import CN_TZ, api_error
from .data_service import normalize_stock_code

MIN_MAIN_BOARD_COVERAGE = 0.995
DEFAULT_READY_AFTER = time(18, 0)

MAIN_BOARD_SH_PREFIXES = ("600", "601", "603", "605")
MAIN_BOARD_SZ_PREFIXES = ("000", "001", "002", "003")


def is_main_board(instrument: WarehouseInstrument) -> bool:
    if instrument.exchange == "SH":
        return instrument.code.startswith(MAIN_BOARD_SH_PREFIXES)
    if instrument.exchange == "SZ":
        return instrument.code.startswith(MAIN_BOARD_SZ_PREFIXES)
    return False


def is_st(instrument: WarehouseInstrument) -> bool:
    normalized = instrument.name.upper().replace(" ", "")
    return normalized.startswith(("*ST", "ST", "S*ST"))


def main_board_non_st_stocks(
    db: Session | None = None,
    *,
    store: WarehouseMarketDataStore | None = None,
) -> list[WarehouseInstrument]:
    market_store = store or WarehouseMarketDataStore()
    stocks = market_store.list_instruments()
    return [stock for stock in stocks if stock.status.lower() == "active" and is_main_board(stock) and not is_st(stock)]


def resolve_default_screener_trade_date(*, now: datetime | None = None) -> date | None:
    current = now or datetime.now(CN_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=CN_TZ)
    current = current.astimezone(CN_TZ)
    today = current.date()
    open_dates = WarehouseMarketDataStore().open_trade_dates(end_date=today)
    if not open_dates:
        return None
    if open_dates[-1] == today and current.time() < DEFAULT_READY_AFTER:
        return open_dates[-2] if len(open_dates) >= 2 else None
    return open_dates[-1]


def target_date_coverage(target_date: date, stocks: list[WarehouseInstrument]) -> tuple[int, int, float]:
    expected = len(stocks)
    if expected == 0:
        return 0, 0, 0.0
    counts = WarehouseMarketDataStore().daily_bar_counts_by_date(
        codes={stock.code for stock in stocks},
        end_date=target_date,
    )
    available = counts.get(target_date, 0)
    return available, expected, available / expected


def ensure_main_board_coverage(
    target_date: date,
    stocks: list[WarehouseInstrument],
    *,
    provider: str,
    min_coverage: float = MIN_MAIN_BOARD_COVERAGE,
) -> None:
    if len(stocks) < 5:
        return
    available, expected, coverage = target_date_coverage(target_date, stocks)
    if coverage < min_coverage:
        raise api_error(
            422,
            "SCREENER_DATA_COVERAGE_TOO_LOW",
            f"{target_date.isoformat()} 未复权日 K 行情覆盖不足，可能是数据同步失败；请先补齐行情后再生成选股快照。",
            {
                "tradeDate": target_date.isoformat(),
                "availableBars": available,
                "expectedBars": expected,
                "coverage": round(coverage, 4),
                "provider": provider,
            },
        )


def ensure_stock_from_warehouse(db: Session, code: str) -> m.Stock:
    normalized_code, _, _ = normalize_stock_code(code)
    stock = db.get(m.Stock, normalized_code)
    if stock is not None:
        return stock

    store = WarehouseMarketDataStore()
    instrument = next((item for item in store.list_instruments() if item.code == normalized_code), None)
    if instrument is None:
        raise api_error(404, "STOCK_NOT_FOUND", f"股票 {code} 不存在于 warehouse 主数据")

    latest_bar = store.latest_bar(normalized_code)
    if latest_bar is None:
        raise api_error(404, "SCREENER_NO_PRICE_DATA", f"股票 {code} 缺少日 K 数据，无法加入观察池")

    previous_bar = store.get_daily_bars(
        normalized_code,
        end_date=latest_bar.trade_date - timedelta(days=1),
        limit=1,
    )
    prev = previous_bar[-1] if previous_bar else None
    change = round(latest_bar.close - prev.close, 2) if prev else 0.0
    change_percent = round((change / prev.close) * 100, 2) if prev and prev.close else 0.0

    stock = m.Stock(
        code=normalized_code,
        symbol=instrument.symbol,
        exchange=instrument.exchange,
        name=instrument.name,
        market=instrument.market,
        industry=instrument.industry or "未知",
        price=latest_bar.close,
        change=change,
        change_percent=change_percent,
        volume=latest_bar.volume,
        amount=latest_bar.amount,
    )
    db.add(stock)
    db.flush()
    return stock


def instrument_market_label(instrument: WarehouseInstrument) -> str:
    if instrument.exchange == "SH":
        return "上证主板"
    if instrument.exchange == "SZ":
        return "深证主板"
    return instrument.market or "主板"


def warehouse_bar_change_percent(bar: WarehousePriceBar, previous_close: float | None) -> float | None:
    if previous_close is None or not previous_close:
        return None
    return round(((bar.close - previous_close) / previous_close) * 100, 2)
