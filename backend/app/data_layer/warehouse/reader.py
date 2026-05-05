from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from ..storage.parquet_store import ParquetStore

RAW_PRICE_ADJUSTMENTS = {"raw", "none"}


@dataclass(frozen=True)
class WarehousePriceBar:
    code: str
    symbol: str
    exchange: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    price_adjustment: str
    source: str
    fetched_at: datetime


class WarehouseMarketDataStore:
    def __init__(self, data_root: Path | str | None = None):
        self.data_root = Path(data_root or os.getenv("DATA_ROOT", "data"))
        self.store = ParquetStore()

    @property
    def daily_bars_path(self) -> Path:
        return self.data_root / "warehouse" / "daily_bars"

    def get_daily_bars(
        self,
        code: str,
        *,
        limit: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        price_adjustment: str = "raw",
    ) -> list[WarehousePriceBar]:
        frame = self._daily_frame(code=code, start_date=start_date, end_date=end_date, price_adjustment=price_adjustment)
        if frame.empty:
            return []
        frame = frame.sort_values("trade_date")
        if limit is not None:
            frame = frame.tail(limit)
        return [_bar_from_row(row) for row in frame.itertuples(index=False)]

    def get_bar(self, code: str, trade_date: date, *, price_adjustment: str = "raw") -> WarehousePriceBar | None:
        bars = self.get_daily_bars(code, start_date=trade_date, end_date=trade_date, price_adjustment=price_adjustment)
        return bars[0] if bars else None

    def latest_bar(self, code: str, *, price_adjustment: str = "raw") -> WarehousePriceBar | None:
        bars = self.get_daily_bars(code, limit=1, price_adjustment=price_adjustment)
        return bars[-1] if bars else None

    def trade_dates(self, *, end_date: date | None = None, price_adjustment: str = "raw") -> list[date]:
        frame = self._read_daily_bars()
        if frame.empty:
            return []
        frame = self._filter_adjustment(frame, price_adjustment)
        if end_date is not None:
            frame = frame[frame["trade_date"] <= end_date]
        return sorted(frame["trade_date"].dropna().unique().tolist())

    def latest_trade_date(self, *, price_adjustment: str = "raw") -> date | None:
        dates = self.trade_dates(price_adjustment=price_adjustment)
        return dates[-1] if dates else None

    def count_daily_bars(self, code: str, *, price_adjustment: str = "raw") -> int:
        return len(self._daily_frame(code=code, price_adjustment=price_adjustment))

    def _daily_frame(
        self,
        *,
        code: str,
        start_date: date | None = None,
        end_date: date | None = None,
        price_adjustment: str = "raw",
    ) -> pd.DataFrame:
        normalized = str(code).zfill(6)
        partition = self.daily_bars_path / f"code={normalized}"
        frame = self.store.read_dataset(partition) if partition.exists() else self._read_daily_bars()
        if frame.empty:
            return frame
        if "code" not in frame.columns:
            frame["code"] = normalized
        frame["code"] = frame["code"].astype(str).str.zfill(6)
        frame = frame[frame["code"] == normalized]
        frame = self._filter_adjustment(frame, price_adjustment)
        if start_date is not None:
            frame = frame[frame["trade_date"] >= start_date]
        if end_date is not None:
            frame = frame[frame["trade_date"] <= end_date]
        return frame

    def _read_daily_bars(self) -> pd.DataFrame:
        if not self.daily_bars_path.exists():
            return pd.DataFrame()
        frame = self.store.read_dataset(self.daily_bars_path)
        if not frame.empty and "trade_date" in frame.columns:
            frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.date
        return frame

    def _filter_adjustment(self, frame: pd.DataFrame, price_adjustment: str) -> pd.DataFrame:
        if "trade_date" in frame.columns:
            frame = frame.copy()
            frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.date
        if "price_adjustment" not in frame.columns:
            return frame
        requested = price_adjustment.lower()
        values = frame["price_adjustment"].astype(str).str.lower()
        if requested == "raw":
            return frame[values.isin(RAW_PRICE_ADJUSTMENTS)]
        return frame[values == requested]


def _bar_from_row(row) -> WarehousePriceBar:
    source_updated_at = getattr(row, "source_updated_at", None)
    if isinstance(source_updated_at, pd.Timestamp):
        fetched_at = source_updated_at.to_pydatetime()
    elif isinstance(source_updated_at, datetime):
        fetched_at = source_updated_at
    else:
        fetched_at = datetime.now(UTC)
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    adjustment = str(getattr(row, "price_adjustment", "raw"))
    if adjustment == "none":
        adjustment = "raw"
    return WarehousePriceBar(
        code=str(row.code).zfill(6),
        symbol=str(row.symbol),
        exchange=str(row.exchange),
        trade_date=row.trade_date,
        open=float(row.open),
        high=float(row.high),
        low=float(row.low),
        close=float(row.close),
        volume=int(row.volume),
        amount=float(row.amount),
        price_adjustment=adjustment,
        source="warehouse",
        fetched_at=fetched_at,
    )
