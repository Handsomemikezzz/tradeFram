from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DataLayerInstrument:
    code: str
    symbol: str
    exchange: str
    name: str
    market: str
    industry: str
    list_date: date | None
    delist_date: date | None
    status: str


@dataclass(frozen=True)
class DataLayerTradingDay:
    trade_date: date
    exchange: str
    is_open: bool


@dataclass(frozen=True)
class DataLayerDailyBar:
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
    price_adjustment: str = "none"


@dataclass(frozen=True)
class DataLayerIndexDailyBar:
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


@dataclass(frozen=True)
class DataLayerAdjFactor:
    code: str
    symbol: str
    trade_date: date
    adj_factor: float


class DataLayerProvider(ABC):
    """Provider boundary for full-market local warehouse sync."""

    name = "base"

    @abstractmethod
    def list_instruments(self) -> list[DataLayerInstrument]:
        raise NotImplementedError

    @abstractmethod
    def get_trading_calendar(self, start_date: date, end_date: date) -> list[DataLayerTradingDay]:
        raise NotImplementedError

    @abstractmethod
    def get_daily_bars(self, code: str, start_date: date, end_date: date, *, price_adjustment: str = "raw") -> list[DataLayerDailyBar]:
        raise NotImplementedError

    def get_daily_bars_bulk(self, target_date: date, *, price_adjustment: str = "raw") -> list[DataLayerDailyBar] | None:
        return None

    @abstractmethod
    def get_index_daily_bars(self, index_code: str, start_date: date, end_date: date) -> list[DataLayerIndexDailyBar]:
        raise NotImplementedError
