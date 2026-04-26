from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.services.data_service import fetch_market_dataset


PROFILE_DATA = {
    "600519": {"name": "贵州茅台", "market": "上证主板", "industry": "白酒"},
    "000858": {"name": "五粮液", "market": "深证主板", "industry": "白酒"},
    "300750": {"name": "宁德时代", "market": "创业板", "industry": "锂电池"},
    "601318": {"name": "中国平安", "market": "上证主板", "industry": "保险"},
    "600879": {"name": "航天电子", "market": "上证主板", "industry": "航天军工"},
}


class FakeAkShare:
    def __init__(self, *, profiles: dict | None = None, bars: dict[str, list[float]] | None = None, financial: bool = True):
        self.profiles = PROFILE_DATA if profiles is None else profiles
        self.bars = bars or {}
        self.financial = financial
        self.profile_calls = 0
        self.bar_calls = 0

    def stock_individual_info_em(self, symbol: str):
        self.profile_calls += 1
        profile = self.profiles.get(symbol)
        if profile is None:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {"item": "股票简称", "value": profile["name"]},
                {"item": "上市市场", "value": profile["market"]},
                {"item": "行业", "value": profile["industry"]},
            ]
        )

    def stock_zh_a_hist(self, symbol: str, period: str, start_date: str, end_date: str, adjust: str):
        self.bar_calls += 1
        closes = self.bars.get(symbol, _series_for(symbol))
        start = date(2026, 2, 25)
        rows = []
        for index, close in enumerate(closes):
            trade_date = start + timedelta(days=index)
            rows.append(
                {
                    "日期": trade_date.isoformat(),
                    "开盘": round(close * 0.995, 2),
                    "最高": round(close * 1.015, 2),
                    "最低": round(close * 0.985, 2),
                    "收盘": round(close, 2),
                    "成交量": 100_000 + index * 1200,
                    "成交额": round((100_000 + index * 1200) * close, 2),
                }
            )
        return pd.DataFrame(rows)

    def stock_financial_abstract(self, symbol: str):
        if not self.financial:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {
                    "报告期": "2026-Q1",
                    "净资产收益率": 22.4,
                    "营业总收入": 400010000000,
                    "归母净利润": 44050000000,
                    "销售毛利率": 20.2,
                    "销售净利率": 11.0,
                }
            ]
        )

    def tool_trade_date_hist_sina(self):
        start = date(2026, 1, 1)
        return pd.DataFrame([{"trade_date": (start + timedelta(days=index)).isoformat()} for index in range(150)])


def install_akshare_fixture(monkeypatch, *, profiles: dict | None = None, bars: dict[str, list[float]] | None = None, financial: bool = True) -> FakeAkShare:
    fake = FakeAkShare(profiles=profiles, bars=bars, financial=financial)
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "akshare")
    monkeypatch.setenv("AKSHARE_ENABLED", "true")
    monkeypatch.setattr("backend.app.providers.akshare_provider._akshare", lambda: fake)
    return fake


def prepare_akshare_stock(db: Session, code: str, *, force_refresh: bool = True):
    dataset = fetch_market_dataset(db, code, force_refresh=force_refresh)
    db.commit()
    return dataset


def _series_for(code: str) -> list[float]:
    if code == "300750":
        return [180.0 + (i * 0.05) for i in range(55)] + [193.0, 195.0, 197.0, 199.0, 201.0]
    if code == "000858":
        return [145.0 + (i * 0.03) for i in range(55)] + [150.0, 152.0, 154.0, 156.0, 158.0]
    if code == "601318":
        return [48.0 - (i * 0.02) for i in range(55)] + [45.0, 44.5, 44.0, 43.5, 43.0]
    if code == "600519":
        return [1650.0 for _ in range(60)]
    return [10.0 + (i * 0.02) for i in range(60)]
