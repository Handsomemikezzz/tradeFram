from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Iterable

import pandas as pd

from ..providers.base import DataLayerDailyBar, DataLayerIndexDailyBar, DataLayerInstrument, DataLayerTradingDay
from .schemas import WAREHOUSE_SCHEMAS


def normalize_instruments(
    records: Iterable[DataLayerInstrument],
    *,
    source_provider: str,
    source_updated_at: datetime,
) -> pd.DataFrame:
    return _with_source(records, "instruments", source_provider, source_updated_at)


def normalize_trading_calendar(
    records: Iterable[DataLayerTradingDay],
    *,
    source_provider: str,
    source_updated_at: datetime,
) -> pd.DataFrame:
    return _with_source(records, "trading_calendar", source_provider, source_updated_at)


def normalize_daily_bars(
    records: Iterable[DataLayerDailyBar],
    *,
    source_provider: str,
    source_updated_at: datetime,
) -> pd.DataFrame:
    return _with_source(records, "daily_bars", source_provider, source_updated_at)


def normalize_index_daily_bars(
    records: Iterable[DataLayerIndexDailyBar],
    *,
    source_provider: str,
    source_updated_at: datetime,
) -> pd.DataFrame:
    return _with_source(records, "index_daily_bars", source_provider, source_updated_at)


def _with_source(records: Iterable[object], dataset: str, source_provider: str, source_updated_at: datetime) -> pd.DataFrame:
    rows = []
    for record in records:
        row = asdict(record)
        row["source_provider"] = source_provider
        row["source_updated_at"] = source_updated_at
        rows.append(row)
    return pd.DataFrame(rows, columns=WAREHOUSE_SCHEMAS[dataset])
