from __future__ import annotations

from datetime import date
import os
from typing import Any

from .base import MarketDataProvider, ProviderDailyBar, ProviderFinancialSnapshot, ProviderStockProfile, ProviderTradingDay


class AkShareMarketDataProvider(MarketDataProvider):
    """Optional single-stock AkShare adapter for v0.1 Beta+.

    The adapter deliberately avoids full-market scanning and real brokerage/AI
    integrations. It fetches only the requested symbol's profile, daily bars,
    financial snapshot, and exchange calendar.
    """

    name = "AkShare"

    def get_stock_profile(self, code: str) -> ProviderStockProfile | None:
        ak = _akshare()
        profile_error: Exception | None = None
        try:
            frame = ak.stock_individual_info_em(symbol=code)
        except Exception as exc:  # pragma: no cover - external network/interface
            profile_error = exc
            frame = None
        if frame is not None and not frame.empty:
            values = _frame_item_map(frame)
            return _profile_from_values(code, values)
        if frame is not None and frame.empty:
            return None

        if profile_error is not None:
            try:
                fallback = _profile_from_exchange_name_table(ak, code)
            except Exception as exc:  # pragma: no cover - external network/interface
                raise RuntimeError(f"AkShare stock profile fetch failed: {profile_error}; fallback name table failed: {exc}") from profile_error
            if fallback is not None:
                return fallback
            raise RuntimeError(f"AkShare stock profile fetch failed: {profile_error}") from profile_error
        return None

    def get_daily_bars(self, code: str, start_date: date, end_date: date) -> list[ProviderDailyBar]:
        ak = _akshare()
        bar_error: Exception | None = None
        try:
            frame = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="",
            )
        except Exception as exc:  # pragma: no cover - external network/interface
            bar_error = exc
            frame = None
        if frame is None and bar_error is not None:
            frame = self._fallback_daily_bars_frame(ak, code, start_date, end_date, bar_error)
        if frame is None or frame.empty:
            return []
        return _daily_bars_from_frame(code, frame)

    def _fallback_daily_bars_frame(self, ak, code: str, start_date: date, end_date: date, original_error: Exception | None):
        symbol = f"{_exchange_for(code).lower()}{code}"
        try:
            return ak.stock_zh_a_daily(symbol=symbol, start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"), adjust="")
        except Exception as sina_error:  # pragma: no cover - external network/interface
            try:
                return ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"), adjust="")
            except Exception as tx_error:
                if original_error is not None:
                    raise RuntimeError(f"{original_error}; fallback daily sources failed: sina={sina_error}; tx={tx_error}") from original_error
                raise RuntimeError(f"fallback daily sources failed: sina={sina_error}; tx={tx_error}") from tx_error

    def get_financial_snapshot(self, code: str) -> ProviderFinancialSnapshot | None:
        ak = _akshare()
        try:
            frame = ak.stock_financial_abstract(symbol=code)
        except Exception:
            return None
        if frame is None or frame.empty:
            return None
        latest = frame.iloc[0]
        report_period = str(_pick(latest, ["报告期", "日期", "公告日期"], "UNKNOWN"))
        return ProviderFinancialSnapshot(
            code=code,
            pe=0.0,
            roe=_to_float(_pick(latest, ["净资产收益率", "ROE", "加权净资产收益率"], 0)),
            revenue=_format_yi(_pick(latest, ["营业总收入", "营业收入"], 0)),
            profit=_format_yi(_pick(latest, ["归母净利润", "净利润"], 0)),
            gross_margin=_to_float(_pick(latest, ["销售毛利率", "毛利率"], 0)),
            net_margin=_to_float(_pick(latest, ["销售净利率", "净利率"], 0)),
            report_period=report_period,
        )

    def get_trading_calendar(self, start_date: date, end_date: date) -> list[ProviderTradingDay]:
        ak = _akshare()
        try:
            frame = ak.tool_trade_date_hist_sina()
        except Exception:
            return []
        if frame is None or frame.empty:
            return []
        days: list[ProviderTradingDay] = []
        for _, row in frame.iterrows():
            trade_date = _to_date(_pick(row, ["trade_date", "日期", "calendarDate"]))
            if start_date <= trade_date <= end_date:
                days.append(ProviderTradingDay(trade_date=trade_date, is_open=True, exchange="CN"))
        return days


def _profile_from_values(code: str, values: dict[str, Any]) -> ProviderStockProfile:
    exchange = _exchange_for(code)
    name = _first_present(values, ["股票简称", "简称", "名称"], code)
    industry = _first_present(values, ["行业", "所属行业"], "UNKNOWN")
    market = _first_present(values, ["上市市场", "市场"], "上证A股" if exchange == "SH" else "深证A股")
    return ProviderStockProfile(code=code, symbol=f"{code}.{exchange}", exchange=exchange, name=str(name), market=str(market), industry=str(industry))


def _profile_from_exchange_name_table(ak, code: str) -> ProviderStockProfile | None:
    exchange = _exchange_for(code)
    if exchange == "SH":
        frame = ak.stock_info_sh_name_code()
        code_keys = ["证券代码", "code", "A股代码"]
        name_keys = ["证券简称", "name", "A股简称", "公司简称"]
        industry_keys = ["所属行业", "行业"]
        market = "上证A股"
    elif exchange == "SZ":
        frame = ak.stock_info_sz_name_code()
        code_keys = ["A股代码", "证券代码", "code"]
        name_keys = ["A股简称", "证券简称", "name", "公司简称"]
        industry_keys = ["所属行业", "行业"]
        market = "深证A股"
    else:
        frame = ak.stock_info_bj_name_code()
        code_keys = ["证券代码", "A股代码", "code"]
        name_keys = ["证券简称", "A股简称", "name", "公司简称"]
        industry_keys = ["所属行业", "行业"]
        market = "北京A股"
    row = _first_row_by_code(frame, code, code_keys)
    if row is None:
        return None
    name = _pick(row, name_keys, code)
    industry = _pick(row, industry_keys, "UNKNOWN")
    return ProviderStockProfile(code=code, symbol=f"{code}.{exchange}", exchange=exchange, name=str(name), market=market, industry=str(industry))


def _daily_bars_from_frame(code: str, frame) -> list[ProviderDailyBar]:
    bars: list[ProviderDailyBar] = []
    for _, row in frame.iterrows():
        bars.append(
            ProviderDailyBar(
                code=code,
                trade_date=_to_date(_pick(row, ["日期", "date", "trade_date"])),
                open=_to_float(_pick(row, ["开盘", "open"])),
                high=_to_float(_pick(row, ["最高", "high"])),
                low=_to_float(_pick(row, ["最低", "low"])),
                close=_to_float(_pick(row, ["收盘", "close"])),
                volume=int(_to_float(_pick(row, ["成交量", "volume", "amount"], 0))),
                amount=_to_float(_pick(row, ["成交额", "amount"], 0)),
            )
        )
    return bars


def _akshare():
    _configure_akshare_proxy_bypass()
    try:
        import akshare as ak  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("akshare is not installed; install requirements.txt before using AkShare data") from exc
    return ak


def _configure_akshare_proxy_bypass() -> None:
    if os.getenv("AKSHARE_BYPASS_PROXY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    default_hosts = "push2.eastmoney.com,push2his.eastmoney.com,*.eastmoney.com,eastmoney.com,finance.sina.com.cn,*.sina.com.cn,proxy.finance.qq.com,*.qq.com"
    for key in ("NO_PROXY", "no_proxy"):
        current = os.getenv(key, "")
        values = [value.strip() for value in current.split(",") if value.strip()]
        for host in default_hosts.split(","):
            if host not in values:
                values.append(host)
        os.environ[key] = ",".join(values)


def _exchange_for(code: str) -> str:
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    return "SH"


def _frame_item_map(frame) -> dict[str, Any]:
    if frame is None or frame.empty:
        return {}
    columns = list(frame.columns)
    item_col = "item" if "item" in columns else ("项目" if "项目" in columns else columns[0])
    value_col = "value" if "value" in columns else ("值" if "值" in columns else columns[-1])
    return {str(row[item_col]): row[value_col] for _, row in frame.iterrows()}


def _first_present(mapping: dict[str, Any], keys: list[str], default: Any) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in {None, ""}:
            return value
    return default


def _first_row_by_code(frame, code: str, code_keys: list[str]):
    if frame is None or frame.empty:
        return None
    for _, row in frame.iterrows():
        value = _pick(row, code_keys)
        if value is not None and str(value).zfill(6) == code:
            return row
    return None


def _pick(row, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        try:
            if key in row and row[key] not in {None, ""}:
                return row[key]
        except TypeError:
            continue
    return default


def _to_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    text = str(value).replace(",", "").replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def _format_yi(value: Any) -> str:
    number = _to_float(value)
    if number == 0:
        return "0 亿"
    # AkShare may return Yuan-level values; if already small, keep as-is.
    if abs(number) > 100_000_000:
        number = number / 100_000_000
    return f"{number:.2f} 亿"


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
