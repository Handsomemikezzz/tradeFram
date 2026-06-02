from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

PATTERN_A_STRATEGY_TYPE = "pattern_a"
PATTERN_A_STRATEGY_NAME = "走势 A"
PATTERN_A_STRATEGY_VERSION = "v2"
SIGNAL_WINDOW_DAYS = 30
MIN_LISTING_BARS = 60
MIN_VALID_BARS_IN_WINDOW = 25
MIN_AVG_AMOUNT_20D = 100_000_000.0

DECLINE_MIN_PCT = 8.0
DECLINE_MIN_SPAN_DAYS = 3
DECLINE_RECENT_LOOKBACK = 15
ANCHOR_MIN_DROP_PCT = -5.0
ANCHOR_BODY_MULTIPLIER = 1.5
STABILIZATION_MIN_DAYS = 3
STABILIZATION_MAX_DAYS = 8
STABILIZATION_LOW_TOLERANCE = 0.005
STABILIZATION_CAPITULATION_TOLERANCE = 0.002
STABILIZATION_SMALL_CANDLE_RATIO = 0.5
STABILIZATION_VOLUME_VS_ANCHOR = 0.7
STABILIZATION_VOLUME_VS_DECLINE = 0.8
BREAKOUT_MIN_CHANGE_PCT = 3.0
BREAKOUT_LIMIT_UP_PCT = 9.8
BREAKOUT_MIN_BODY_RATIO = 0.5
BREAKOUT_VOLUME_VS_BOX = 1.5
BREAKOUT_VOLUME_VS_MA5 = 1.2
SECOND_SURGE_LOOKBACK = 3
SECOND_SURGE_MIN_CHANGE_PCT = 3.0
MA5_FLAT_MAX_DROP_PCT = 0.3
SMALL_MOVE_MAX_PCT = 2.0
DOJI_MAX_BODY_RATIO = 0.2
EX_RIGHTS_GAP_PCT = 11.0
EX_RIGHTS_MAX_BODY_RATIO = 0.3

PatternAStatus = Literal["CONFIRMED", "PENDING_CONFIRMATION"]


@dataclass(frozen=True)
class PatternABar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_percent: float | None


@dataclass(frozen=True)
class PatternACandidate:
    status: PatternAStatus
    signal_date: date
    score: int
    price_action_score: int
    moving_average_score: int
    volume_score: int
    change_percent: float | None
    tags: list[str]
    reason: dict


@dataclass(frozen=True)
class _StabilizationBox:
    start_index: int
    end_index: int
    box_high: float
    box_low: float
    avg_volume: float


def evaluate_pattern_a(bars: list[PatternABar], target_date: date) -> PatternACandidate | None:
    if not bars:
        return None
    ordered = sorted(bars, key=lambda bar: bar.trade_date)
    if target_date not in {bar.trade_date for bar in ordered}:
        return None
    if len(ordered) < MIN_LISTING_BARS:
        return None

    window = [bar for bar in ordered if bar.trade_date <= target_date][-SIGNAL_WINDOW_DAYS:]
    if len(window) < MIN_VALID_BARS_IN_WINDOW:
        return None
    if _avg_amount(window[-20:]) < MIN_AVG_AMOUNT_20D:
        return None
    if has_suspected_ex_rights(window):
        return None

    target_index = next(index for index, bar in enumerate(window) if bar.trade_date == target_date)
    decline = _find_decline_leg(window, target_index)
    if decline is None:
        return None

    l_min_index, l_min, h_max_index = decline
    anchor_indices = _iter_anchor_indices(window, h_max_index, l_min_index, target_index)
    if not anchor_indices:
        return None

    for anchor_index in anchor_indices:
        anchor_bar = window[anchor_index]
        confirmed = _evaluate_confirmed(window, target_index, anchor_index, anchor_bar, l_min)
        if confirmed is not None:
            return confirmed

    for anchor_index in anchor_indices:
        anchor_bar = window[anchor_index]
        pending = _evaluate_pending(window, target_index, anchor_index, anchor_bar, l_min)
        if pending is not None:
            return pending
    return None


def has_suspected_ex_rights(window: list[PatternABar]) -> bool:
    for index in range(1, len(window)):
        if _is_suspected_ex_rights(window[index - 1], window[index]):
            return True
    return False


def _evaluate_confirmed(
    window: list[PatternABar],
    target_index: int,
    anchor_index: int,
    anchor_bar: PatternABar,
    anchor_low: float,
) -> PatternACandidate | None:
    min_stab_end = anchor_index + STABILIZATION_MIN_DAYS
    for stab_end in range(target_index - 1, min_stab_end - 1, -1):
        for length in range(STABILIZATION_MAX_DAYS, STABILIZATION_MIN_DAYS - 1, -1):
            stab_start = stab_end - length + 1
            if stab_start <= anchor_index:
                continue
            box = _validate_stabilization(window, anchor_index, stab_start, stab_end, anchor_bar, anchor_low)
            if box is None:
                continue
            if not _is_breakout(window, target_index, box):
                continue
            return _build_candidate(
                window,
                status="CONFIRMED",
                target_index=target_index,
                anchor_bar=anchor_bar,
                box=box,
            )
    return None


def _evaluate_pending(
    window: list[PatternABar],
    target_index: int,
    anchor_index: int,
    anchor_bar: PatternABar,
    anchor_low: float,
) -> PatternACandidate | None:
    min_stab_end = anchor_index + STABILIZATION_MIN_DAYS
    for stab_end in range(target_index - 1, min_stab_end - 1, -1):
        for length in range(STABILIZATION_MAX_DAYS, STABILIZATION_MIN_DAYS - 1, -1):
            stab_start = stab_end - length + 1
            if stab_start <= anchor_index:
                continue
            box = _validate_stabilization(window, anchor_index, stab_start, stab_end, anchor_bar, anchor_low)
            if box is None:
                continue
            if _is_breakout(window, target_index, box):
                return None
            if window[target_index].close > box.box_high:
                return None
            return _build_candidate(
                window,
                status="PENDING_CONFIRMATION",
                target_index=target_index,
                anchor_bar=anchor_bar,
                box=box,
            )
    return None


def _find_decline_leg(window: list[PatternABar], target_index: int) -> tuple[int, float, int] | None:
    if target_index < DECLINE_MIN_SPAN_DAYS:
        return None
    search_start = max(0, target_index - DECLINE_RECENT_LOOKBACK)
    pre_target = window[search_start:target_index]
    if len(pre_target) < DECLINE_MIN_SPAN_DAYS:
        return None

    local_min_index = min(range(len(pre_target)), key=lambda index: pre_target[index].low)
    l_min_index = search_start + local_min_index
    l_min = window[l_min_index].low
    pre_low = window[search_start : l_min_index + 1]
    local_high_index = max(range(len(pre_low)), key=lambda index: pre_low[index].high)
    h_max_index = search_start + local_high_index
    h_max = window[h_max_index].high
    if h_max <= 0 or l_min_index - h_max_index + 1 < DECLINE_MIN_SPAN_DAYS:
        return None
    if (h_max - l_min) / h_max * 100 < DECLINE_MIN_PCT:
        return None

    tail = window[max(search_start, l_min_index - 4) : l_min_index + 1]
    if len(tail) >= 2 and tail[-1].close >= tail[0].close:
        return None
    if l_min_index >= 5:
        ma5_start = _ma_at(window, l_min_index - 5, 5)
        ma5_end = _ma_at(window, l_min_index, 5)
        if ma5_start is not None and ma5_end is not None and ma5_end >= ma5_start * 0.99:
            return None
    return l_min_index, l_min, h_max_index


def _iter_anchor_indices(
    window: list[PatternABar],
    h_max_index: int,
    l_min_index: int,
    target_index: int,
) -> list[int]:
    min_room = STABILIZATION_MIN_DAYS
    candidates: list[int] = []
    for index in range(l_min_index, h_max_index - 1, -1):
        bar = window[index]
        if bar.close >= bar.open:
            continue
        if target_index - index < min_room:
            continue
        change = _change_pct(window, index)
        avg_body = _avg_body(window, index, 5)
        body = _body_size(bar)
        strong_drop = change is not None and change <= ANCHOR_MIN_DROP_PCT
        strong_body = avg_body > 0 and body >= avg_body * ANCHOR_BODY_MULTIPLIER
        if not strong_drop and not strong_body:
            continue
        candidates.append(index)
    return candidates


def _validate_stabilization(
    window: list[PatternABar],
    anchor_index: int,
    stab_start: int,
    stab_end: int,
    anchor_bar: PatternABar,
    anchor_low: float,
) -> _StabilizationBox | None:
    segment = window[stab_start : stab_end + 1]
    if len(segment) < STABILIZATION_MIN_DAYS or len(segment) > STABILIZATION_MAX_DAYS:
        return None

    floor = anchor_low * (1 - STABILIZATION_LOW_TOLERANCE)
    if any(bar.low < floor for bar in segment):
        return None

    eligible_indices = [
        index
        for index in range(stab_start, stab_end + 1)
        if not _is_capitulation_bar(window[index], anchor_low) and index != stab_end
    ]
    if not eligible_indices:
        eligible_indices = [
            index
            for index in range(stab_start, stab_end + 1)
            if not _is_capitulation_bar(window[index], anchor_low)
        ]
    if not eligible_indices:
        return None
    small_count = sum(1 for index in eligible_indices if _is_small_stabilization_candle(window, index))
    if small_count / len(eligible_indices) < STABILIZATION_SMALL_CANDLE_RATIO:
        return None

    avg_volume = sum(bar.volume for bar in segment) / len(segment)
    decline_segment = window[max(0, anchor_index - 10) : anchor_index + 1]
    decline_avg_volume = sum(bar.volume for bar in decline_segment) / len(decline_segment)
    if avg_volume > anchor_bar.volume * STABILIZATION_VOLUME_VS_ANCHOR:
        return None
    if avg_volume > decline_avg_volume * STABILIZATION_VOLUME_VS_DECLINE:
        return None

    return _StabilizationBox(
        start_index=stab_start,
        end_index=stab_end,
        box_high=max(bar.high for bar in segment),
        box_low=min(bar.low for bar in segment),
        avg_volume=avg_volume,
    )


def _is_breakout(window: list[PatternABar], target_index: int, box: _StabilizationBox) -> bool:
    bar = window[target_index]
    if bar.close <= bar.open or bar.high == bar.low:
        return False

    change = _change_pct(window, target_index)
    if change is None:
        return False
    if change < BREAKOUT_MIN_CHANGE_PCT and change < BREAKOUT_LIMIT_UP_PCT:
        return False

    amplitude = bar.high - bar.low
    body = _body_size(bar)
    if body / amplitude < BREAKOUT_MIN_BODY_RATIO:
        return False
    if bar.close < bar.low + amplitude / 2:
        return False
    if bar.close <= box.box_high:
        return False

    recent5 = [item.volume for item in window[max(0, target_index - 4) : target_index + 1]]
    avg5 = sum(recent5) / len(recent5) if recent5 else 0
    if bar.volume < box.avg_volume * BREAKOUT_VOLUME_VS_BOX:
        return False
    if avg5 and bar.volume < avg5 * BREAKOUT_VOLUME_VS_MA5:
        return False
    return True


def _is_second_surge(window: list[PatternABar], target_index: int) -> bool:
    for index in range(max(1, target_index - SECOND_SURGE_LOOKBACK), target_index):
        change = _change_pct(window, index)
        if change is not None and change >= SECOND_SURGE_MIN_CHANGE_PCT and window[index].close > window[index].open:
            return True
    return False


def _is_capitulation_bar(bar: PatternABar, anchor_low: float) -> bool:
    return bar.low <= anchor_low * (1 + STABILIZATION_CAPITULATION_TOLERANCE)


def _is_small_stabilization_candle(window: list[PatternABar], index: int) -> bool:
    bar = window[index]
    change = _change_pct(window, index)
    amplitude = bar.high - bar.low
    body = _body_size(bar)
    if amplitude <= 0:
        return True
    if body / amplitude <= DOJI_MAX_BODY_RATIO:
        return True
    if change is None:
        return False
    if abs(change) <= SMALL_MOVE_MAX_PCT:
        return True
    return False


def _build_candidate(
    window: list[PatternABar],
    *,
    status: PatternAStatus,
    target_index: int,
    anchor_bar: PatternABar,
    box: _StabilizationBox,
) -> PatternACandidate:
    target_bar = window[target_index]
    price_action_score, ma_score, volume_score, tags = _score_candidate(window, status, target_index, box)
    total = min(100, round(price_action_score + ma_score + volume_score))
    reason = {
        "strategyType": PATTERN_A_STRATEGY_TYPE,
        "strategyVersion": PATTERN_A_STRATEGY_VERSION,
        "anchorBar": _bar_reason(anchor_bar),
        "keyBearishBar": _bar_reason(anchor_bar),
        "stabilization": {
            "startDate": window[box.start_index].trade_date.isoformat(),
            "endDate": window[box.end_index].trade_date.isoformat(),
            "boxHigh": round(box.box_high, 4),
            "boxLow": round(box.box_low, 4),
        },
        "confirmBar": _bar_reason(target_bar) if status == "CONFIRMED" else None,
        "scores": {
            "total": total,
            "priceAction": price_action_score,
            "movingAverage": ma_score,
            "volume": volume_score,
        },
        "tags": tags,
    }
    change_percent = _change_pct(window, target_index)
    return PatternACandidate(
        status=status,
        signal_date=target_bar.trade_date,
        score=total,
        price_action_score=price_action_score,
        moving_average_score=ma_score,
        volume_score=volume_score,
        change_percent=change_percent,
        tags=tags,
        reason=reason,
    )


def _score_candidate(
    window: list[PatternABar],
    status: PatternAStatus,
    target_index: int,
    box: _StabilizationBox,
) -> tuple[int, int, int, list[str]]:
    tags: list[str] = []
    price_action = 40 if status == "CONFIRMED" else 30
    if status == "CONFIRMED":
        tags.append("突破整理区")
        price_action = 50
        if _is_second_surge(window, target_index):
            tags.append("二次强攻")
            price_action = min(50, price_action + 5)

    ma_score = 0
    ma5 = _ma_at(window, target_index, 5)
    ma10 = _ma_at(window, target_index, 10)
    ma20 = _ma_at(window, target_index, 20)
    if _ma5_flat_or_turning(window, target_index):
        tags.append("MA5拐头")
        ma_score += 8
    if ma5 is not None and ma10 is not None and ma5 >= ma10:
        tags.append("MA5站上MA10")
        ma_score += 6
    if ma5 is not None and ma10 is not None and ma20 is not None and ma5 >= ma10 >= ma20:
        tags.append("MA多头排列")
        ma_score += 6
    ma_score = min(ma_score, 20)

    volume_score = 0
    target_bar = window[target_index]
    if status == "CONFIRMED" and target_bar.volume >= box.avg_volume * BREAKOUT_VOLUME_VS_BOX:
        tags.append("地量后放量")
        volume_score += 20
    elif target_bar.volume < box.avg_volume:
        tags.append("缩量企稳")
        volume_score += 10
    volume_score = min(volume_score, 30)

    return price_action, ma_score, volume_score, tags[:3]


def _is_suspected_ex_rights(previous: PatternABar, current: PatternABar) -> bool:
    if not previous.close:
        return False
    gap_pct = abs((current.open - previous.close) / previous.close) * 100
    if gap_pct <= EX_RIGHTS_GAP_PCT:
        return False
    amplitude = current.high - current.low
    body = _body_size(current)
    if amplitude <= 0:
        return True
    if body / amplitude <= EX_RIGHTS_MAX_BODY_RATIO:
        return True
    change = current.change_percent
    if change is not None:
        body_up = current.close >= current.open
        if body_up != (change >= 0):
            return True
    return False


def _ma5_flat_or_turning(window: list[PatternABar], index: int) -> bool:
    current = _ma_at(window, index, 5)
    previous = _ma_at(window, index - 1, 5)
    if current is None or previous is None:
        return False
    if current >= previous:
        return True
    drop_pct = (previous - current) / previous * 100 if previous else 0
    return drop_pct <= MA5_FLAT_MAX_DROP_PCT


def _bar_reason(bar: PatternABar) -> dict:
    return {
        "tradeDate": bar.trade_date.isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "bodyTop": max(bar.open, bar.close),
        "bodyBottom": min(bar.open, bar.close),
    }


def _change_pct(window: list[PatternABar], index: int) -> float | None:
    bar = window[index]
    if bar.change_percent is not None:
        return bar.change_percent
    if index <= 0 or not window[index - 1].close:
        return None
    return round(((bar.close - window[index - 1].close) / window[index - 1].close) * 100, 2)


def _body_size(bar: PatternABar) -> float:
    return abs(bar.close - bar.open)


def _amplitude_ratio(bar: PatternABar) -> float:
    if bar.close <= 0:
        return 0.0
    return (bar.high - bar.low) / bar.close


def _avg_body(window: list[PatternABar], index: int, period: int) -> float:
    segment = window[max(0, index + 1 - period) : index + 1]
    if not segment:
        return 0.0
    return sum(_body_size(bar) for bar in segment) / len(segment)


def _avg_amount(bars: list[PatternABar]) -> float:
    if not bars:
        return 0.0
    return sum(bar.amount for bar in bars) / len(bars)


def _ma_at(window: list[PatternABar], index: int, period: int) -> float | None:
    if index + 1 < period:
        return None
    closes = [bar.close for bar in window[index + 1 - period : index + 1]]
    return sum(closes) / len(closes)
