from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.indicators import (
    MovingAverageSnapshot,
    moving_average_snapshot_from_bars,
    trend_label,
)


@dataclass
class FakeBar:
    close: float


def test_empty_bars_returns_all_none():
    snap = moving_average_snapshot_from_bars([])
    assert snap.latest_close is None
    assert snap.ma5 is None
    assert snap.ma20 is None
    assert snap.trend_label == "数据不足"
    assert snap.bar_count == 0


def test_single_bar():
    snap = moving_average_snapshot_from_bars([FakeBar(close=10)])
    assert snap.latest_close == 10
    assert snap.ma5 == 10
    assert snap.ma20 == 10
    assert snap.bar_count == 1


def test_trend_label_strong():
    assert trend_label(10.2, 10.0) == "短期偏强"


def test_trend_label_weak():
    assert trend_label(9.8, 10.0) == "短期偏弱"


def test_trend_label_neutral():
    assert trend_label(10.0, 10.0) == "震荡"
