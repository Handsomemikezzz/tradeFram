from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from ..data_layer.warehouse.reader import WarehouseMarketDataStore


class PriceBarLike(Protocol):
    close: float


@dataclass(frozen=True)
class MovingAverageSnapshot:
    latest_close: float | None
    ma5: float | None
    ma20: float | None
    trend_label: str
    bar_count: int


def moving_average_snapshot_from_bars(bars: Sequence[PriceBarLike]) -> MovingAverageSnapshot:
    ordered = list(bars)
    if not ordered:
        return MovingAverageSnapshot(
            latest_close=None,
            ma5=None,
            ma20=None,
            trend_label="数据不足",
            bar_count=0,
        )

    latest_close = float(ordered[-1].close)
    ma5 = sum(float(bar.close) for bar in ordered[-5:]) / min(len(ordered), 5)
    ma20 = sum(float(bar.close) for bar in ordered[-20:]) / min(len(ordered), 20)
    return MovingAverageSnapshot(
        latest_close=latest_close,
        ma5=ma5,
        ma20=ma20,
        trend_label=trend_label(ma5, ma20),
        bar_count=len(ordered),
    )


def moving_average_snapshot_for_code(
    code: str,
    *,
    store: WarehouseMarketDataStore | None = None,
    limit: int = 20,
) -> MovingAverageSnapshot:
    market_store = store or WarehouseMarketDataStore()
    return moving_average_snapshot_from_bars(market_store.get_daily_bars(code, limit=limit))


def trend_label(ma5: float | None, ma20: float | None) -> str:
    if ma5 is None or ma20 is None:
        return "数据不足"
    if ma5 > ma20 * 1.01:
        return "短期偏强"
    if ma5 < ma20 * 0.99:
        return "短期偏弱"
    return "震荡"
