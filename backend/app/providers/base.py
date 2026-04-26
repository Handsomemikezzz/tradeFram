from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ProviderStockProfile:
    code: str
    symbol: str
    exchange: str
    name: str
    market: str
    industry: str


@dataclass(frozen=True)
class ProviderDailyBar:
    code: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


@dataclass(frozen=True)
class ProviderFinancialSnapshot:
    code: str
    pe: float
    roe: float
    revenue: str
    profit: str
    gross_margin: float
    net_margin: float
    report_period: str


@dataclass(frozen=True)
class ProviderTradingDay:
    trade_date: date
    is_open: bool
    exchange: str


class MarketDataProvider(ABC):
    """Unified data provider boundary for v0.1 Beta.

    Providers may return real stock profile/daily bars/financial snapshots, but they
    must not place orders, make trading decisions, or scan the full market.
    """

    name = "base"

    @abstractmethod
    def get_stock_profile(self, code: str) -> ProviderStockProfile | None:
        raise NotImplementedError

    @abstractmethod
    def get_daily_bars(self, code: str, start_date: date, end_date: date) -> list[ProviderDailyBar]:
        raise NotImplementedError

    @abstractmethod
    def get_financial_snapshot(self, code: str) -> ProviderFinancialSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    def get_trading_calendar(self, start_date: date, end_date: date) -> list[ProviderTradingDay]:
        raise NotImplementedError
