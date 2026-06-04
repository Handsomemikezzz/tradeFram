from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..data_layer.warehouse.reader import WarehouseMarketDataStore, WarehousePriceBar
from .stock_universe import warehouse_bar_change_percent


MAX_LOOKBACK = 120
DEFAULT_LOOKBACK = 30
PATTERN_A_DETAIL_LOOKBACK = 120


@dataclass(frozen=True)
class DailyBarPoint:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_percent: float | None
    ma5: float | None
    ma10: float | None
    ma20: float | None


class DailyBarError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def get_daily_bar_series(
    code: str,
    *,
    end_date: date | None = None,
    lookback: int = DEFAULT_LOOKBACK,
    store: WarehouseMarketDataStore | None = None,
) -> list[DailyBarPoint]:
    if lookback < 1:
        raise DailyBarError("INVALID_LOOKBACK", "lookback 必须大于 0")
    if lookback > MAX_LOOKBACK:
        raise DailyBarError("INVALID_LOOKBACK", f"lookback 不能超过 {MAX_LOOKBACK}")

    market_store = store or WarehouseMarketDataStore()
    normalized = str(code).zfill(6)
    fetch_limit = lookback + 25
    bars = market_store.get_daily_bars(normalized, end_date=end_date, limit=fetch_limit)
    if not bars:
        raise DailyBarError("SCREENER_NO_PRICE_DATA", f"{normalized} 缺少日 K 数据", status_code=404)

    tail = bars[-lookback:]
    closes = [bar.close for bar in bars]
    points: list[DailyBarPoint] = []
    for index, bar in enumerate(tail):
        global_index = len(bars) - len(tail) + index
        previous_close = closes[global_index - 1] if global_index > 0 else None
        points.append(
            DailyBarPoint(
                trade_date=bar.trade_date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                amount=bar.amount,
                change_percent=warehouse_bar_change_percent(bar, previous_close),
                ma5=_moving_average(closes, global_index, 5),
                ma10=_moving_average(closes, global_index, 10),
                ma20=_moving_average(closes, global_index, 20),
            )
        )
    return points


def daily_bar_payload(point: DailyBarPoint) -> dict:
    return {
        "tradeDate": point.trade_date.isoformat(),
        "open": point.open,
        "high": point.high,
        "low": point.low,
        "close": point.close,
        "volume": point.volume,
        "amount": point.amount,
        "changePercent": point.change_percent,
        "ma5": point.ma5,
        "ma10": point.ma10,
        "ma20": point.ma20,
    }


def build_markers_from_reason(reason: dict) -> list[dict]:
    markers: list[dict] = []
    key_bar = reason.get("keyBearishBar") or {}
    if key_bar.get("tradeDate"):
        markers.append(
            {
                "tradeDate": key_bar["tradeDate"],
                "kind": "key_bearish",
                "label": "关键阴线",
            }
        )
    stabilization = reason.get("stabilization") or {}
    if stabilization.get("startDate") and stabilization.get("endDate"):
        markers.append(
            {
                "tradeDate": stabilization["startDate"],
                "endDate": stabilization["endDate"],
                "kind": "stabilization",
                "label": "企稳区间",
            }
        )
    confirm_bar = reason.get("confirmBar") or {}
    if confirm_bar.get("tradeDate"):
        markers.append(
            {
                "tradeDate": confirm_bar["tradeDate"],
                "kind": "confirm",
                "label": "确认阳线",
            }
        )
    return markers


def _moving_average(closes: list[float], index: int, window: int) -> float | None:
    if index + 1 < window:
        return None
    segment = closes[index + 1 - window : index + 1]
    return round(sum(segment) / window, 4)
