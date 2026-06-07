from __future__ import annotations

from datetime import date, timedelta

from backend.app.services.uptrend import (
    UptrendBar,
    UptrendIndexBar,
    calculate_regulatory_deviation,
    evaluate_uptrend,
    regulatory_index_for_stock,
)


def qbar(day: date, close: float, *, open_: float | None = None, high: float | None = None, low: float | None = None, amount: float = 150_000_000) -> UptrendBar:
    open_price = close if open_ is None else open_
    return UptrendBar(
        trade_date=day,
        open=open_price,
        high=high if high is not None else close * 1.02,
        low=low if low is not None else close * 0.98,
        close=close,
        volume=1_000_000,
        amount=amount,
        change_percent=None,
    )


def rawbar(day: date, close: float, previous_close: float | None, *, amount: float = 150_000_000) -> UptrendBar:
    change = None if previous_close is None else round((close / previous_close - 1) * 100, 2)
    return UptrendBar(
        trade_date=day,
        open=close * 0.99,
        high=close * 1.01,
        low=close * 0.98,
        close=close,
        volume=1_000_000,
        amount=amount,
        change_percent=change,
    )


def ibar(day: date, close: float, index_code: str = "000002.SH") -> UptrendIndexBar:
    return UptrendIndexBar(
        index_code=index_code,
        name="上证A股指数",
        trade_date=day,
        close=close,
    )


def series(start: date, closes: list[float], *, amount: float = 150_000_000) -> list[UptrendBar]:
    return [qbar(start + timedelta(days=i), close, amount=amount) for i, close in enumerate(closes)]


def raw_series(start: date, closes: list[float], *, amount: float = 150_000_000) -> list[UptrendBar]:
    bars: list[UptrendBar] = []
    previous = None
    for i, close in enumerate(closes):
        bars.append(rawbar(start + timedelta(days=i), close, previous, amount=amount))
        previous = close
    return bars


def index_series(start: date, closes: list[float], index_code: str = "000002.SH") -> list[UptrendIndexBar]:
    return [ibar(start + timedelta(days=i), close, index_code=index_code) for i, close in enumerate(closes)]


def _make_uptrend_data(start: date, closes: list[float], *, late_amount: float = 200_000_000, late_count: int = 10):
    """Build qfq, raw, and index bars with elevated volume in the last `late_count` bars."""
    qfq = []
    raw = []
    prev = None
    for i, c in enumerate(closes):
        amount = late_amount if i >= len(closes) - late_count else 150_000_000
        day = start + timedelta(days=i)
        change = None if prev is None else round((c / prev - 1) * 100, 2)
        qfq.append(UptrendBar(trade_date=day, open=c, high=c * 1.02, low=c * 0.98, close=c, volume=1_000_000, amount=amount, change_percent=None))
        raw.append(UptrendBar(trade_date=day, open=c * 0.99, high=c * 1.01, low=c * 0.98, close=c, volume=1_000_000, amount=amount, change_percent=change))
        prev = c
    idx = [ibar(start + timedelta(days=i), 1000 + i * 0.5) for i in range(len(closes))]
    return qfq, raw, idx


def test_regulatory_index_for_main_board_stock():
    assert regulatory_index_for_stock("600001") == ("000002.SH", "上证A股指数")
    assert regulatory_index_for_stock("000001") == ("399107.SZ", "深证A股指数")


def test_calculate_regulatory_deviation_uses_stock_minus_index_return():
    start = date(2026, 1, 1)
    stock = series(start, [10, 11, 12, 13])
    index = index_series(start, [1000, 1010, 1020, 1030])

    result = calculate_regulatory_deviation(stock, index, window_days=3)

    assert result.deviation_percent == round(((13 / 10 - 1) * 100) - ((1030 / 1000 - 1) * 100), 2)
    assert result.stock_return_percent == 30.0
    assert result.index_return_percent == 3.0


def test_evaluate_uptrend_accepts_confirmed_healthy_pullback():
    start = date(2026, 1, 1)
    # 40 bars base + 20 bars uptrend; MA alignment builds then price consolidates just above MA10
    base = [10 + i * 0.12 for i in range(40)]
    uptrend = [14.9, 15.1, 15.4, 15.7, 15.9, 16.0, 16.2, 16.4, 16.5, 16.6,
               16.7, 16.8, 16.85, 16.8, 16.75, 16.8, 16.82, 16.84, 16.82, 16.8]
    closes = base + uptrend
    qfq, raw, index = _make_uptrend_data(start, closes, late_amount=200_000_000, late_count=10)

    result = evaluate_uptrend("600001", qfq, raw, index, qfq[-1].trade_date)

    assert result is not None
    assert result.status == "CONFIRMED"
    assert result.reason["setupType"] in {"HEALTHY_PULLBACK", "STRONG_PUSH"}
    assert result.reason["regulatory"]["deviation30Percent"] < 200
    assert any(tag in result.tags for tag in ["健康回踩", "MA多头排列", "强势推进"])


def test_evaluate_uptrend_excludes_when_30_day_deviation_reaches_200():
    start = date(2026, 1, 1)
    closes = [10 + i * 0.05 for i in range(30)] + [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56]
    qfq = series(start, closes)
    raw = raw_series(start, closes)
    index = index_series(start, [1000 + i * 1.0 for i in range(len(closes))])

    result = evaluate_uptrend("600001", qfq, raw, index, qfq[-1].trade_date)

    assert result is None


def test_evaluate_uptrend_excludes_dense_recent_limit_ups():
    start = date(2026, 1, 1)
    closes = [10 + i * 0.08 for i in range(57)]
    qfq = series(start, closes)
    raw = raw_series(start, closes[:-3] + [closes[-4] * 1.10, closes[-4] * 1.21, closes[-4] * 1.22])
    index = index_series(start, [1000 + i * 1.0 for i in range(len(closes))])

    result = evaluate_uptrend("600001", qfq, raw, index, qfq[-1].trade_date)

    assert result is None
