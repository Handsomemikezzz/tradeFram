from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.app.data_layer.warehouse.reader import WarehouseMarketDataStore
from backend.app.services.pattern_a import (
    PATTERN_A_STRATEGY_VERSION,
    PatternABar,
    evaluate_pattern_a,
    has_suspected_ex_rights,
)
from backend.app.services.screeners import warehouse_bar_change_percent_from_values


def bar(
    trade_date: date,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 1_000_000,
    amount: float = 200_000_000.0,
    change_percent: float | None = None,
) -> PatternABar:
    return PatternABar(
        trade_date=trade_date,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        amount=amount,
        change_percent=change_percent,
    )


PROJECT_DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def load_warehouse_bars(code: str, end: date, limit: int = 120) -> list[PatternABar]:
    raw = WarehouseMarketDataStore(PROJECT_DATA_ROOT).get_daily_bars(code, end_date=end, limit=limit)
    bars: list[PatternABar] = []
    for index, item in enumerate(raw):
        previous_close = raw[index - 1].close if index else None
        bars.append(
            PatternABar(
                trade_date=item.trade_date,
                open=item.open,
                high=item.high,
                low=item.low,
                close=item.close,
                volume=item.volume,
                amount=item.amount,
                change_percent=warehouse_bar_change_percent_from_values(item.close, previous_close),
            )
        )
    return bars


def test_ex_rights_filter_detects_large_gap():
    window = [
        bar(date(2026, 5, 1), open_=10, high=10.2, low=9.8, close=10),
        bar(date(2026, 5, 2), open_=8.5, high=8.55, low=8.48, close=8.5, change_percent=-15),
    ]
    assert has_suspected_ex_rights(window) is True


def test_strategy_version_is_v2():
    assert PATTERN_A_STRATEGY_VERSION == "v2"


def test_jinlangiao_002081_confirmed_on_20260601():
    bars = load_warehouse_bars("002081", date(2026, 6, 1))
    result = evaluate_pattern_a(bars, date(2026, 6, 1))
    assert result is not None
    assert result.status == "CONFIRMED"
    assert "突破整理区" in result.tags


def test_shenzhenhuaqiang_000062_confirmed_on_20260602():
    bars = load_warehouse_bars("000062", date(2026, 6, 2))
    result = evaluate_pattern_a(bars, date(2026, 6, 2))
    assert result is not None
    assert result.status == "CONFIRMED"
    assert "突破整理区" in result.tags


def test_shenzhenhuaqiang_000062_pending_on_20260601():
    bars = load_warehouse_bars("000062", date(2026, 6, 1))
    result = evaluate_pattern_a(bars, date(2026, 6, 1))
    assert result is not None
    assert result.status == "PENDING_CONFIRMATION"
