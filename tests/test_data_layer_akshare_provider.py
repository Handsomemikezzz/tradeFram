from __future__ import annotations

from datetime import date

import pandas as pd

from backend.app.data_layer.providers.akshare import AkShareDataLayerProvider


class FakeAkShare:
    def __init__(self):
        self.index_em_symbols: list[str] = []

    def stock_info_a_code_name(self):
        return pd.DataFrame(
            [
                {"code": "600519", "name": "贵州茅台"},
                {"code": "000001", "name": "平安银行"},
            ]
        )

    def stock_zh_a_hist(self, **kwargs):
        assert kwargs["adjust"] == ""
        return pd.DataFrame(
            [
                {
                    "日期": "2026-04-30",
                    "开盘": 100,
                    "最高": 110,
                    "最低": 99,
                    "收盘": 108,
                    "成交量": 1000,
                    "成交额": 108000,
                }
            ]
        )

    def index_zh_a_hist(self, **kwargs):
        return pd.DataFrame(
            [
                {
                    "日期": "2026-04-30",
                    "开盘": 3000,
                    "最高": 3010,
                    "最低": 2990,
                    "收盘": 3005,
                    "成交量": 100,
                    "成交额": 100000,
                }
            ]
        )

    def stock_zh_index_daily_em(self, **kwargs):
        self.index_em_symbols.append(kwargs["symbol"])
        return pd.DataFrame(
            [
                {
                    "date": "2026-04-30",
                    "open": 3000,
                    "high": 3010,
                    "low": 2990,
                    "close": 3005,
                    "volume": 100,
                    "amount": 100000,
                }
            ]
        )

    def stock_zh_index_daily(self, **kwargs):
        return pd.DataFrame(
            [
                {
                    "date": date(2026, 4, 30),
                    "open": 3000,
                    "high": 3010,
                    "low": 2990,
                    "close": 3005,
                    "volume": 100,
                }
            ]
        )

    def tool_trade_date_hist_sina(self):
        return pd.DataFrame([{"trade_date": "2026-04-29"}, {"trade_date": "2026-04-30"}])


def test_akshare_data_layer_provider_converts_instruments(monkeypatch):
    monkeypatch.setattr("backend.app.data_layer.providers.akshare._akshare", lambda: FakeAkShare())

    instruments = AkShareDataLayerProvider().list_instruments()

    assert [item.code for item in instruments] == ["600519", "000001"]
    assert instruments[0].symbol == "600519.SH"
    assert instruments[1].symbol == "000001.SZ"
    assert instruments[0].status == "active"


def test_akshare_data_layer_provider_converts_daily_bars(monkeypatch):
    monkeypatch.setattr("backend.app.data_layer.providers.akshare._akshare", lambda: FakeAkShare())

    bars = AkShareDataLayerProvider().get_daily_bars("600519", date(2026, 4, 1), date(2026, 4, 30))

    assert len(bars) == 1
    assert bars[0].symbol == "600519.SH"
    assert bars[0].price_adjustment == "none"
    assert bars[0].close == 108


def test_akshare_data_layer_provider_converts_calendar_and_index_bars(monkeypatch):
    fake = FakeAkShare()
    monkeypatch.setattr("backend.app.data_layer.providers.akshare._akshare", lambda: fake)
    provider = AkShareDataLayerProvider()

    calendar = provider.get_trading_calendar(date(2026, 4, 30), date(2026, 4, 30))
    index_bars = provider.get_index_daily_bars("000001.SH", date(2026, 4, 1), date(2026, 4, 30))

    assert [day.trade_date for day in calendar] == [date(2026, 4, 30)]
    assert calendar[0].exchange == "CN_A"
    assert index_bars[0].index_code == "000001.SH"
    assert index_bars[0].name == "上证指数"
    assert fake.index_em_symbols == ["sh000001"]


def test_akshare_index_daily_bars_use_sz_prefix_for_sz_indexes(monkeypatch):
    fake = FakeAkShare()
    monkeypatch.setattr("backend.app.data_layer.providers.akshare._akshare", lambda: fake)

    bars = AkShareDataLayerProvider().get_index_daily_bars("399001.SZ", date(2026, 4, 1), date(2026, 4, 30))

    assert bars[0].index_code == "399001.SZ"
    assert fake.index_em_symbols == ["sz399001"]


def test_akshare_index_daily_bars_fallback_to_index_hist(monkeypatch):
    class EmFailAkShare(FakeAkShare):
        def stock_zh_index_daily_em(self, **kwargs):
            raise RuntimeError("em unavailable")

    monkeypatch.setattr("backend.app.data_layer.providers.akshare._akshare", lambda: EmFailAkShare())

    bars = AkShareDataLayerProvider().get_index_daily_bars("000300.SH", date(2026, 4, 1), date(2026, 4, 30))

    assert len(bars) == 1
    assert bars[0].index_code == "000300.SH"
    assert bars[0].amount == 100000


def test_akshare_index_daily_bars_fallback_to_legacy_daily_without_amount(monkeypatch):
    class EmAndHistFailAkShare(FakeAkShare):
        def stock_zh_index_daily_em(self, **kwargs):
            raise RuntimeError("em unavailable")

        def index_zh_a_hist(self, **kwargs):
            raise RuntimeError("hist unavailable")

    monkeypatch.setattr("backend.app.data_layer.providers.akshare._akshare", lambda: EmAndHistFailAkShare())

    bars = AkShareDataLayerProvider().get_index_daily_bars("000905.SH", date(2026, 4, 1), date(2026, 4, 30))

    assert len(bars) == 1
    assert bars[0].index_code == "000905.SH"
    assert bars[0].amount == 0
