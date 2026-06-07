from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
from pyarrow.lib import ArrowNotImplementedError

from ..storage.parquet_store import ParquetStore

RAW_PRICE_ADJUSTMENTS = {"raw", "none"}


@dataclass(frozen=True)
class WarehouseInstrument:
    code: str
    symbol: str
    exchange: str
    name: str
    market: str
    industry: str
    status: str


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


@dataclass(frozen=True)
class WarehouseIndexBar:
    index_code: str
    symbol: str
    name: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    source: str
    fetched_at: datetime


class WarehouseMarketDataStore:
    def __init__(self, data_root: Path | str | None = None):
        self.data_root = Path(data_root or os.getenv("DATA_ROOT", "data"))
        self.store = ParquetStore()

    @property
    def daily_bars_path(self) -> Path:
        return self.data_root / "warehouse" / "daily_bars"

    @property
    def instruments_path(self) -> Path:
        return self.data_root / "warehouse" / "instruments"

    @property
    def index_daily_bars_path(self) -> Path:
        return self.data_root / "warehouse" / "index_daily_bars"

    @property
    def trading_calendar_path(self) -> Path:
        return self.data_root / "warehouse" / "trading_calendar"

    def list_instruments(self) -> list[WarehouseInstrument]:
        if not self.instruments_path.exists():
            return []
        frame = self.store.read_dataset(self.instruments_path)
        if frame.empty:
            return []
        frame["code"] = frame["code"].astype(str).str.zfill(6)
        return [
            WarehouseInstrument(
                code=str(row.code).zfill(6),
                symbol=str(row.symbol),
                exchange=str(row.exchange),
                name=str(row.name),
                market=str(row.market),
                industry=str(row.industry),
                status=str(getattr(row, "status", "active")),
            )
            for row in frame.sort_values("code").itertuples(index=False)
        ]

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

    def daily_bars_frame(
        self,
        *,
        codes: set[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        price_adjustment: str = "raw",
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        required_columns = set(columns or [])
        required_columns.update({"code", "trade_date", "price_adjustment"})
        filters = _daily_bar_filters(start_date=start_date, end_date=end_date, price_adjustment=price_adjustment)
        frame = self._read_daily_bars(columns=sorted(required_columns) if columns is not None else None, filters=filters)
        if frame.empty:
            return frame
        frame = self._filter_adjustment(frame, price_adjustment)
        if frame.empty:
            return frame
        if start_date is not None:
            frame = frame[frame["trade_date"] >= start_date]
        if end_date is not None:
            frame = frame[frame["trade_date"] <= end_date]
        if codes is not None:
            normalized_codes = {str(code).zfill(6) for code in codes}
            frame = frame.copy()
            frame["code"] = frame["code"].astype(str).str.zfill(6)
            frame = frame[frame["code"].isin(normalized_codes)]
        return frame

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

    def open_trade_dates(self, *, end_date: date | None = None) -> list[date]:
        if not self.trading_calendar_path.exists():
            return self.trade_dates(end_date=end_date)
        frame = self.store.read_dataset(self.trading_calendar_path)
        if frame.empty:
            return self.trade_dates(end_date=end_date)
        frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.date
        if "is_open" in frame.columns:
            frame = frame[frame["is_open"].astype(bool)]
        if end_date is not None:
            frame = frame[frame["trade_date"] <= end_date]
        dates = sorted(frame["trade_date"].dropna().unique().tolist())
        return dates or self.trade_dates(end_date=end_date)

    def daily_bar_counts_by_date(
        self,
        *,
        codes: set[str] | None = None,
        end_date: date | None = None,
        price_adjustment: str = "raw",
    ) -> dict[date, int]:
        frame = self._read_daily_bars()
        if frame.empty:
            return {}
        frame = self._filter_adjustment(frame, price_adjustment)
        if frame.empty:
            return {}
        if end_date is not None:
            frame = frame[frame["trade_date"] <= end_date]
        if codes is not None:
            normalized_codes = {str(code).zfill(6) for code in codes}
            frame = frame.copy()
            frame["code"] = frame["code"].astype(str).str.zfill(6)
            frame = frame[frame["code"].isin(normalized_codes)]
        if frame.empty:
            return {}
        counts = frame.groupby("trade_date")["code"].nunique()
        return {day: int(count) for day, count in counts.items()}

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
        if partition.exists():
            frame = self.store.read_dataset(partition)
        else:
            filters = _daily_bar_filters(start_date=start_date, end_date=end_date, price_adjustment=price_adjustment)
            code_filter = int(normalized)
            filters.append(("code", "==", code_filter))
            try:
                frame = self._read_daily_bars(filters=filters)
            except (ArrowNotImplementedError, TypeError, ValueError):
                filters[-1] = ("code", "==", normalized)
                frame = self._read_daily_bars(filters=filters)
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

    def _read_daily_bars(self, *, columns: list[str] | None = None, filters=None) -> pd.DataFrame:
        if not self.daily_bars_path.exists():
            return pd.DataFrame()
        frame = self.store.read_dataset(self.daily_bars_path, columns=columns, filters=filters)
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


    def get_index_daily_bars(
        self,
        index_code: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
    ) -> list[WarehouseIndexBar]:
        frame = self.index_daily_bars_frame(index_code=index_code, start_date=start_date, end_date=end_date)
        if frame.empty:
            return []
        frame = frame.sort_values("trade_date")
        if limit is not None:
            frame = frame.tail(limit)
        return [_index_bar_from_row(row) for row in frame.itertuples(index=False)]

    def index_daily_bars_frame(
        self,
        *,
        index_code: str,
        start_date: date | None = None,
        end_date: date | None = None,
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        if not self.index_daily_bars_path.exists():
            return pd.DataFrame()
        required_columns = set(columns or [])
        required_columns.update({"index_code", "trade_date"})
        normalized = str(index_code).upper()
        partition = self.index_daily_bars_path / f"index_code={normalized}"
        if partition.exists():
            frame = self.store.read_dataset(partition, columns=sorted(required_columns) if columns is not None else None)
        else:
            frame = self.store.read_dataset(
                self.index_daily_bars_path,
                columns=sorted(required_columns) if columns is not None else None,
            )
        if frame.empty:
            return frame
        if "index_code" not in frame.columns:
            frame["index_code"] = normalized
        frame["index_code"] = frame["index_code"].astype(str).str.upper()
        frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.date
        frame = frame[frame["index_code"] == normalized]
        if start_date is not None:
            frame = frame[frame["trade_date"] >= start_date]
        if end_date is not None:
            frame = frame[frame["trade_date"] <= end_date]
        return frame


def _daily_bar_filters(*, start_date: date | None, end_date: date | None, price_adjustment: str):
    filters = []
    if start_date is not None:
        filters.append(("trade_date", ">=", start_date))
    if end_date is not None:
        filters.append(("trade_date", "<=", end_date))
    requested = price_adjustment.lower()
    if requested == "raw":
        filters.append(("price_adjustment", "in", sorted(RAW_PRICE_ADJUSTMENTS)))
    else:
        filters.append(("price_adjustment", "==", requested))
    return filters or None


def _index_bar_from_row(row) -> WarehouseIndexBar:
    source_updated_at = getattr(row, "source_updated_at", None)
    if isinstance(source_updated_at, pd.Timestamp):
        fetched_at = source_updated_at.to_pydatetime()
    elif isinstance(source_updated_at, datetime):
        fetched_at = source_updated_at
    else:
        fetched_at = datetime.now(UTC)
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    return WarehouseIndexBar(
        index_code=str(row.index_code).upper(),
        symbol=str(row.symbol),
        name=str(row.name),
        trade_date=row.trade_date,
        open=float(row.open),
        high=float(row.high),
        low=float(row.low),
        close=float(row.close),
        volume=int(row.volume),
        amount=float(row.amount),
        source="warehouse",
        fetched_at=fetched_at,
    )


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
