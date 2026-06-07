from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

UPTREND_STRATEGY_TYPE = "uptrend"
UPTREND_STRATEGY_NAME = "上行趋势"
UPTREND_STRATEGY_VERSION = "v1"

MIN_LISTING_BARS = 60
MIN_AVG_AMOUNT_20D = 100_000_000.0
REGULATORY_30D_EXCLUDE_THRESHOLD = 200.0
REGULATORY_30D_WARNING_THRESHOLD = 180.0
MAIN_BOARD_LIMIT_UP_PCT = 9.8

UptrendStatus = Literal["CONFIRMED"]
SetupType = Literal["HEALTHY_PULLBACK", "STRONG_PUSH"]


@dataclass(frozen=True)
class UptrendBar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_percent: float | None


@dataclass(frozen=True)
class UptrendIndexBar:
    index_code: str
    name: str
    trade_date: date
    close: float


@dataclass(frozen=True)
class RegulatoryDeviation:
    window_days: int
    stock_return_percent: float
    index_return_percent: float
    deviation_percent: float


@dataclass(frozen=True)
class UptrendCandidate:
    status: UptrendStatus
    signal_date: date
    score: int
    price_action_score: int
    moving_average_score: int
    volume_score: int
    change_percent: float | None
    tags: list[str]
    reason: dict


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def regulatory_index_for_stock(code: str) -> tuple[str, str]:
    normalized = str(code).zfill(6)
    if normalized.startswith(("600", "601", "603", "605")):
        return "000002.SH", "上证A股指数"
    if normalized.startswith(("000", "001", "002", "003")):
        return "399107.SZ", "深证A股指数"
    raise ValueError(f"unsupported board for regulatory deviation: {code}")


def calculate_regulatory_deviation(
    stock_bars: list[UptrendBar],
    index_bars: list[UptrendIndexBar],
    *,
    window_days: int,
) -> RegulatoryDeviation:
    if len(stock_bars) < window_days + 1 or len(index_bars) < window_days + 1:
        raise ValueError(f"window_days={window_days} requires {window_days + 1} bars")
    stock_start = stock_bars[-window_days - 1].close
    stock_end = stock_bars[-1].close
    index_start = index_bars[-window_days - 1].close
    index_end = index_bars[-1].close
    if stock_start <= 0 or index_start <= 0:
        raise ValueError("start close must be positive")
    stock_return = (stock_end / stock_start - 1) * 100
    index_return = (index_end / index_start - 1) * 100
    return RegulatoryDeviation(
        window_days=window_days,
        stock_return_percent=round(stock_return, 2),
        index_return_percent=round(index_return, 2),
        deviation_percent=round(stock_return - index_return, 2),
    )


def evaluate_uptrend(
    code: str,
    qfq_bars: list[UptrendBar],
    raw_bars: list[UptrendBar],
    index_bars: list[UptrendIndexBar],
    target_date: date,
) -> UptrendCandidate | None:
    qfq = _ordered_until(qfq_bars, target_date)
    raw = _ordered_until(raw_bars, target_date)
    indexes = _ordered_index_until(index_bars, target_date)
    if len(qfq) < MIN_LISTING_BARS or len(raw) < MIN_LISTING_BARS or len(indexes) < 31:
        return None
    if qfq[-1].trade_date != target_date or raw[-1].trade_date != target_date or indexes[-1].trade_date != target_date:
        return None

    regulatory3 = calculate_regulatory_deviation(qfq, indexes, window_days=3)
    regulatory10 = calculate_regulatory_deviation(qfq, indexes, window_days=10)
    regulatory30 = calculate_regulatory_deviation(qfq, indexes, window_days=30)
    if regulatory30.deviation_percent >= REGULATORY_30D_EXCLUDE_THRESHOLD:
        return None

    ma5 = _ma_series(qfq, 5)
    ma10 = _ma_series(qfq, 10)
    ma20 = _ma_series(qfq, 20)
    target_index = len(qfq) - 1
    if not _trend_confirmed(qfq, ma5, ma10, ma20, target_index):
        return None
    if not _price_near_high_or_recent_breakout(qfq, target_index):
        return None
    if not _low_lifted(qfq):
        return None
    if _drawdown_from_high20(qfq, target_index) > 8.0:
        return None

    distance_ma10 = _distance_percent(qfq[-1].close, ma10[-1])
    distance_ma20 = _distance_percent(qfq[-1].close, ma20[-1])
    ma5_to_ma20 = _distance_percent(ma5[-1], ma20[-1])
    if distance_ma10 > 18.0 or distance_ma20 > 35.0:
        return None

    limit_up_count3 = sum(1 for bar in raw[-3:] if _is_main_board_limit_up(bar))
    limit_up_count10 = sum(1 for bar in raw[-10:] if _is_main_board_limit_up(bar))
    if len(raw) >= 2 and _is_main_board_limit_up(raw[-1]) and _is_main_board_limit_up(raw[-2]):
        return None
    if limit_up_count3 >= 2:
        return None

    avg_amount5 = _avg_amount(raw[-5:])
    avg_amount10 = _avg_amount(raw[-10:])
    avg_amount20 = _avg_amount(raw[-20:])
    if avg_amount20 < MIN_AVG_AMOUNT_20D:
        return None
    if avg_amount10 < avg_amount20 * 1.1:
        return None
    if avg_amount5 < avg_amount20 * 0.8:
        return None
    breakout_amount_ratio = _recent_breakout_amount_ratio(qfq, raw, target_index, avg_amount20)
    if breakout_amount_ratio is not None and breakout_amount_ratio < 1.2:
        return None
    if _has_high_volume_stall(qfq, raw, avg_amount20):
        return None

    setup_type, setup_label = _setup_type(qfq, ma5, ma10, target_index)
    regulatory_score = _regulatory_score(regulatory30.deviation_percent)
    entry_score = _entry_score(setup_type, distance_ma10)
    trend_score = _trend_score(qfq, ma5, ma10, ma20, target_index)
    volume_score = _volume_score(avg_amount5, avg_amount10, avg_amount20, breakout_amount_ratio)
    total = min(100, regulatory_score + entry_score + trend_score + volume_score)
    tags = _tags(
        setup_label=setup_label,
        regulatory30=regulatory30,
        limit_up_count10=limit_up_count10,
        distance_ma10=distance_ma10,
        ma5_to_ma20=ma5_to_ma20,
        avg_amount5=avg_amount5,
        avg_amount20=avg_amount20,
    )
    index_code, index_name = regulatory_index_for_stock(code)
    reason = _reason(
        strategy_type=UPTREND_STRATEGY_TYPE,
        setup_type=setup_type,
        setup_label=setup_label,
        index_code=index_code,
        index_name=index_name,
        regulatory3=regulatory3,
        regulatory10=regulatory10,
        regulatory30=regulatory30,
        ma5=ma5[-1],
        ma10=ma10[-1],
        ma20=ma20[-1],
        distance_ma10=distance_ma10,
        distance_ma20=distance_ma20,
        ma5_to_ma20=ma5_to_ma20,
        qfq=qfq,
        raw=raw,
        avg_amount5=avg_amount5,
        avg_amount10=avg_amount10,
        avg_amount20=avg_amount20,
        breakout_amount_ratio=breakout_amount_ratio,
        limit_up_count3=limit_up_count3,
        limit_up_count10=limit_up_count10,
        scores={
            "total": total,
            "regulatory": regulatory_score,
            "entry": entry_score,
            "trend": trend_score,
            "volume": volume_score,
        },
        tags=tags,
    )
    return UptrendCandidate(
        status="CONFIRMED",
        signal_date=qfq[-1].trade_date,
        score=total,
        price_action_score=entry_score,
        moving_average_score=trend_score,
        volume_score=volume_score,
        change_percent=raw[-1].change_percent,
        tags=tags[:4],
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _ordered_until(bars: list[UptrendBar], target_date: date) -> list[UptrendBar]:
    return sorted([bar for bar in bars if bar.trade_date <= target_date], key=lambda bar: bar.trade_date)


def _ordered_index_until(bars: list[UptrendIndexBar], target_date: date) -> list[UptrendIndexBar]:
    return sorted([bar for bar in bars if bar.trade_date <= target_date], key=lambda bar: bar.trade_date)


def _ma_series(bars: list[UptrendBar], window: int) -> list[float | None]:
    values: list[float | None] = []
    closes = [bar.close for bar in bars]
    for index in range(len(closes)):
        if index + 1 < window:
            values.append(None)
        else:
            values.append(round(sum(closes[index + 1 - window: index + 1]) / window, 4))
    return values


def _trend_confirmed(
    bars: list[UptrendBar],
    ma5: list[float | None],
    ma10: list[float | None],
    ma20: list[float | None],
    target_index: int,
) -> bool:
    recent = range(target_index - 4, target_index + 1)
    aligned = sum(1 for index in recent if _ma_aligned(ma5[index], ma10[index], ma20[index]))
    above_ma10 = sum(1 for index in recent if ma10[index] is not None and bars[index].close >= ma10[index])
    if aligned < 4 or above_ma10 < 4:
        return False
    if ma10[target_index] is None or ma20[target_index] is None or ma10[target_index - 3] is None or ma20[target_index - 5] is None:
        return False
    if ma10[target_index] <= ma10[target_index - 3] or ma20[target_index] <= ma20[target_index - 5]:
        return False
    if bars[target_index].close < ma10[target_index] or bars[target_index].close < ma20[target_index]:
        return False
    if bars[target_index - 1].close < ma10[target_index - 1] and bars[target_index].close < ma10[target_index]:
        return False
    return True


def _ma_aligned(ma5: float | None, ma10: float | None, ma20: float | None) -> bool:
    return ma5 is not None and ma10 is not None and ma20 is not None and ma5 > ma10 > ma20


def _price_near_high_or_recent_breakout(bars: list[UptrendBar], target_index: int) -> bool:
    highest_close20 = max(bar.close for bar in bars[target_index - 19: target_index + 1])
    if bars[target_index].close >= highest_close20 * 0.95:
        return True
    for index in range(target_index - 4, target_index + 1):
        segment = bars[index - 19: index + 1]
        if len(segment) == 20 and bars[index].close >= max(bar.close for bar in segment):
            return True
    return False


def _low_lifted(bars: list[UptrendBar]) -> bool:
    previous_low = min(bar.low for bar in bars[-20:-10])
    recent_low = min(bar.low for bar in bars[-10:])
    return recent_low > previous_low


def _drawdown_from_high20(bars: list[UptrendBar], target_index: int) -> float:
    highest_close20 = max(bar.close for bar in bars[target_index - 19: target_index + 1])
    return round((highest_close20 - bars[target_index].close) / highest_close20 * 100, 2)


def _distance_percent(value: float, base: float | None) -> float:
    if base is None or base <= 0:
        return 999.0
    return round((value / base - 1) * 100, 2)


def _is_main_board_limit_up(bar: UptrendBar) -> bool:
    return bar.change_percent is not None and bar.change_percent >= MAIN_BOARD_LIMIT_UP_PCT


def _avg_amount(bars: list[UptrendBar]) -> float:
    return sum(bar.amount for bar in bars) / len(bars) if bars else 0.0


def _recent_breakout_amount_ratio(
    qfq: list[UptrendBar],
    raw: list[UptrendBar],
    target_index: int,
    avg_amount20: float,
) -> float | None:
    """Return the breakout day's amount / avg_amount20 if there was a 20d high close breakout in the last 5 days."""
    if avg_amount20 <= 0:
        return None
    for offset in range(5):
        idx = target_index - offset
        if idx < 20:
            continue
        segment = qfq[idx - 19: idx + 1]
        if len(segment) < 20:
            continue
        if qfq[idx].close >= max(bar.close for bar in segment[:-1]):
            # idx is a 20d breakout day - find corresponding raw bar
            breakout_date = qfq[idx].trade_date
            raw_bar = next((b for b in raw if b.trade_date == breakout_date), None)
            if raw_bar is not None:
                return round(raw_bar.amount / avg_amount20, 4)
    return None


def _has_high_volume_stall(qfq: list[UptrendBar], raw: list[UptrendBar], avg_amount20: float) -> bool:
    """Exclude: recent 3 days with single day amount >= 2.5x AND closed <= open AND close < 20d high * 0.98."""
    if avg_amount20 <= 0:
        return False
    target_index = len(qfq) - 1
    for offset in range(3):
        idx = target_index - offset
        if idx < 0 or idx >= len(raw):
            continue
        raw_bar = raw[idx]
        if raw_bar.amount < avg_amount20 * 2.5:
            continue
        if raw_bar.close > raw_bar.open:
            continue
        if idx >= 19:
            highest_close20 = max(bar.close for bar in qfq[idx - 19: idx + 1])
            if raw_bar.close >= highest_close20 * 0.98:
                continue
        return True
    return False


def _setup_type(qfq: list[UptrendBar], ma5: list[float | None], ma10: list[float | None], target_index: int) -> tuple[str, str]:
    close = qfq[target_index].close
    ma10_val = ma10[target_index]
    ma5_val = ma5[target_index]
    if ma10_val is not None and close >= ma10_val:
        dist = _distance_percent(close, ma10_val)
        if 0 <= dist <= 8:
            highest_close20 = max(bar.close for bar in qfq[target_index - 19: target_index + 1])
            drawdown = (highest_close20 - close) / highest_close20 * 100
            if drawdown <= 8:
                return "HEALTHY_PULLBACK", "健康回踩"
    if ma5_val is not None and close >= ma5_val:
        dist_ma10 = _distance_percent(close, ma10_val)
        if dist_ma10 <= 18:
            return "STRONG_PUSH", "强势推进"
    return "STRONG_PUSH", "强势推进"


def _regulatory_score(deviation30: float) -> int:
    if deviation30 < 100:
        return 30
    if deviation30 < 180:
        return round(30 - (deviation30 - 100) / 80 * 15)
    return 5


def _entry_score(setup_type: str, distance_ma10: float) -> int:
    if setup_type == "HEALTHY_PULLBACK":
        if distance_ma10 <= 4:
            return 25
        return 20
    else:
        if distance_ma10 <= 8:
            return 18
        if distance_ma10 <= 12:
            return 14
        return 8


def _trend_score(
    qfq: list[UptrendBar],
    ma5: list[float | None],
    ma10: list[float | None],
    ma20: list[float | None],
    target_index: int,
) -> int:
    score = 0
    if _ma_aligned(ma5[target_index], ma10[target_index], ma20[target_index]):
        score += 10
    recent = range(target_index - 4, target_index + 1)
    aligned_all = all(_ma_aligned(ma5[i], ma10[i], ma20[i]) for i in recent)
    if aligned_all:
        score += 5
    if ma10[target_index] is not None and ma10[target_index - 3] is not None:
        slope10 = _distance_percent(ma10[target_index], ma10[target_index - 3])
        if slope10 >= 1.0:
            score += 4
    if ma20[target_index] is not None and ma20[target_index - 5] is not None:
        slope20 = _distance_percent(ma20[target_index], ma20[target_index - 5])
        if slope20 >= 1.0:
            score += 3
    highest_close20 = max(bar.close for bar in qfq[target_index - 19: target_index + 1])
    if _distance_percent(qfq[target_index].close, highest_close20) <= 3:
        score += 3
    return min(score, 25)


def _volume_score(avg_amount5: float, avg_amount10: float, avg_amount20: float, breakout_ratio: float | None) -> int:
    score = 0
    if avg_amount20 >= MIN_AVG_AMOUNT_20D:
        score += 8
    if avg_amount10 >= avg_amount20 * 1.2:
        score += 5
    if avg_amount5 >= avg_amount20:
        score += 3
    if breakout_ratio is not None and breakout_ratio >= 1.2:
        score += 4
    return min(score, 20)


def _tags(
    *,
    setup_label: str,
    regulatory30: RegulatoryDeviation,
    limit_up_count10: int,
    distance_ma10: float,
    ma5_to_ma20: float,
    avg_amount5: float,
    avg_amount20: float,
) -> list[str]:
    tags: list[str] = [setup_label]
    tags.append("MA多头排列")
    if avg_amount5 >= avg_amount20:
        tags.append("量能温和放大")
    elif avg_amount5 >= avg_amount20 * 0.8:
        tags.append("量能稳定")
    if regulatory30.deviation_percent >= REGULATORY_30D_WARNING_THRESHOLD:
        tags.append("30日偏离临界")
    if limit_up_count10 >= 2:
        tags.append("近期涨停较多")
    if ma5_to_ma20 > 25:
        tags.append("均线偏离较大")
    if distance_ma10 <= 4:
        tags.append("贴近均线")
    return tags


def _reason(
    *,
    strategy_type: str,
    setup_type: str,
    setup_label: str,
    index_code: str,
    index_name: str,
    regulatory3: RegulatoryDeviation,
    regulatory10: RegulatoryDeviation,
    regulatory30: RegulatoryDeviation,
    ma5: float | None,
    ma10: float | None,
    ma20: float | None,
    distance_ma10: float,
    distance_ma20: float,
    ma5_to_ma20: float,
    qfq: list[UptrendBar],
    raw: list[UptrendBar],
    avg_amount5: float,
    avg_amount10: float,
    avg_amount20: float,
    breakout_amount_ratio: float | None,
    limit_up_count3: int,
    limit_up_count10: int,
    scores: dict,
    tags: list[str],
) -> dict:
    target_index = len(qfq) - 1
    highest_close20 = max(bar.close for bar in qfq[target_index - 19: target_index + 1])
    highest_close20_date = max(
        qfq[target_index - 19: target_index + 1], key=lambda bar: bar.close
    ).trade_date
    drawdown = round((highest_close20 - qfq[-1].close) / highest_close20 * 100, 2)
    ma10_slope3 = _distance_percent(ma10, qfq[target_index - 3].close if target_index >= 3 else None) if ma10 else None
    ma20_slope5 = _distance_percent(ma20, qfq[target_index - 5].close if target_index >= 5 else None) if ma20 else None

    recent_aligned = range(target_index - 4, target_index + 1)
    # compute local
    ma5_series = _ma_series(qfq, 5)
    ma10_series = _ma_series(qfq, 10)
    ma20_series = _ma_series(qfq, 20)
    aligned_days = sum(1 for i in recent_aligned if _ma_aligned(ma5_series[i], ma10_series[i], ma20_series[i]))
    above_ma10_days = sum(1 for i in recent_aligned if ma10_series[i] is not None and qfq[i].close >= ma10_series[i])

    # slope calculations using MA series
    ma10_slope3d = None
    if ma10_series[target_index] is not None and ma10_series[target_index - 3] is not None:
        base = ma10_series[target_index - 3]
        if base and base > 0:
            ma10_slope3d = round((ma10_series[target_index] / base - 1) * 100, 4)
    ma20_slope5d = None
    if ma20_series[target_index] is not None and ma20_series[target_index - 5] is not None:
        base = ma20_series[target_index - 5]
        if base and base > 0:
            ma20_slope5d = round((ma20_series[target_index] / base - 1) * 100, 4)

    return {
        "strategyType": strategy_type,
        "strategyVersion": UPTREND_STRATEGY_VERSION,
        "setupType": setup_type,
        "setupLabel": setup_label,
        "basis": {
            "priceAdjustmentForTrend": "qfq",
            "priceAdjustmentForLimitUp": "raw",
            "regulatoryResetPolicy": "rolling_without_exchange_announcement_reset",
        },
        "regulatory": {
            "indexCode": index_code,
            "indexName": index_name,
            "deviation3Percent": regulatory3.deviation_percent,
            "deviation10Percent": regulatory10.deviation_percent,
            "deviation30Percent": regulatory30.deviation_percent,
            "deviation30ThresholdPercent": REGULATORY_30D_EXCLUDE_THRESHOLD,
            "deviation30MarginPercent": round(REGULATORY_30D_EXCLUDE_THRESHOLD - regulatory30.deviation_percent, 2),
            "deviation30RiskLevel": "HIGH_RISK" if regulatory30.deviation_percent >= REGULATORY_30D_WARNING_THRESHOLD else "NORMAL",
        },
        "trend": {
            "ma5": round(ma5, 4) if ma5 is not None else None,
            "ma10": round(ma10, 4) if ma10 is not None else None,
            "ma20": round(ma20, 4) if ma20 is not None else None,
            "ma10Slope3dPercent": ma10_slope3d,
            "ma20Slope5dPercent": ma20_slope5d,
            "distanceToMa10Percent": distance_ma10,
            "distanceToMa20Percent": distance_ma20,
            "ma5ToMa20DistancePercent": ma5_to_ma20,
            "highestClose20": highest_close20,
            "drawdownFromHigh20Percent": drawdown,
            "recentAlignedDays": aligned_days,
            "recentAboveMa10Days": above_ma10_days,
            "trendStartDate": qfq[target_index - 4].trade_date.isoformat(),
            "recentHighDate": highest_close20_date.isoformat(),
            "pullbackDate": qfq[-1].trade_date.isoformat(),
        },
        "volume": {
            "avgAmount5": avg_amount5,
            "avgAmount10": avg_amount10,
            "avgAmount20": avg_amount20,
            "breakoutAmountRatio": breakout_amount_ratio,
        },
        "limitUp": {
            "limitUpCount3d": limit_up_count3,
            "limitUpCount10d": limit_up_count10,
            "hadRecentLimitUp": limit_up_count10 > 0,
        },
        "scores": scores,
        "tags": tags,
    }
