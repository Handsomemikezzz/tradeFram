from __future__ import annotations

from datetime import date, timedelta

from .base import MarketDataProvider, ProviderDailyBar, ProviderFinancialSnapshot, ProviderStockProfile, ProviderTradingDay


MOCK_PROFILES: dict[str, ProviderStockProfile] = {
    "600519": ProviderStockProfile("600519", "600519.SH", "SH", "贵州茅台", "上证主板", "白酒"),
    "000858": ProviderStockProfile("000858", "000858.SZ", "SZ", "五粮液", "深证主板", "白酒"),
    "300750": ProviderStockProfile("300750", "300750.SZ", "SZ", "宁德时代", "创业板", "锂电池"),
    "601318": ProviderStockProfile("601318", "601318.SH", "SH", "中国平安", "上证主板", "保险"),
}

MOCK_FINANCIALS: dict[str, ProviderFinancialSnapshot] = {
    "600519": ProviderFinancialSnapshot("600519", 28.5, 31.2, "1500.20 亿", "740.10 亿", 91.5, 49.3, "2026-Q1"),
    "000858": ProviderFinancialSnapshot("000858", 18.2, 25.1, "830.50 亿", "300.20 亿", 75.2, 36.1, "2026-Q1"),
    "300750": ProviderFinancialSnapshot("300750", 15.6, 22.4, "4000.10 亿", "440.50 亿", 20.2, 11.0, "2026-Q1"),
    "601318": ProviderFinancialSnapshot("601318", 8.5, 12.1, "12000.50 亿", "1000.20 亿", 100.0, 8.3, "2026-Q1"),
}


class MockMarketDataProvider(MarketDataProvider):
    name = "MockProvider"

    def get_stock_profile(self, code: str) -> ProviderStockProfile | None:
        return MOCK_PROFILES.get(code)

    def get_daily_bars(self, code: str, start_date: date, end_date: date) -> list[ProviderDailyBar]:
        closes = _series_for(code)
        first_date = date(2026, 2, 25)
        bars = [_bar(code, first_date + timedelta(days=index), close, index) for index, close in enumerate(closes)]
        return [bar for bar in bars if start_date <= bar.trade_date <= end_date]

    def get_financial_snapshot(self, code: str) -> ProviderFinancialSnapshot | None:
        return MOCK_FINANCIALS.get(code)

    def get_trading_calendar(self, start_date: date, end_date: date) -> list[ProviderTradingDay]:
        days: list[ProviderTradingDay] = []
        current = start_date
        while current <= end_date:
            days.append(ProviderTradingDay(current, current.weekday() < 5, "CN"))
            current += timedelta(days=1)
        return days


class EmptyMarketDataProvider(MockMarketDataProvider):
    """Test provider: profile exists, bars absent."""

    name = "EmptyProvider"

    def get_daily_bars(self, code: str, start_date: date, end_date: date) -> list[ProviderDailyBar]:
        return []


def _series_for(code: str) -> list[float]:
    if code == "300750":
        return [180.0 + (i * 0.05) for i in range(55)] + [193.0, 195.0, 197.0, 199.0, 201.0]
    if code == "000858":
        return [145.0 + (i * 0.03) for i in range(55)] + [150.0, 152.0, 154.0, 156.0, 158.0]
    if code == "601318":
        return [48.0 - (i * 0.02) for i in range(55)] + [45.0, 44.5, 44.0, 43.5, 43.0]
    if code == "600519":
        return [1650.0 for _ in range(60)]
    # Unknown codes use a neutral series so research can degrade safely when a
    # provider supplies profile data later.
    return [10.0 for _ in range(60)]


def _bar(code: str, trade_date: date, close: float, index: int) -> ProviderDailyBar:
    return ProviderDailyBar(
        code=code,
        trade_date=trade_date,
        open=round(close * 0.995, 2),
        high=round(close * 1.015, 2),
        low=round(close * 0.985, 2),
        close=round(close, 2),
        volume=100_000 + index * 1200,
        amount=round((100_000 + index * 1200) * close, 2),
    )
