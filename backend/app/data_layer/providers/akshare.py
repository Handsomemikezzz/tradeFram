from __future__ import annotations

import os
from datetime import date
from typing import Any

from .base import DataLayerDailyBar, DataLayerIndexDailyBar, DataLayerInstrument, DataLayerProvider, DataLayerTradingDay
from ..warehouse.schemas import CORE_INDEXES


class AkShareDataLayerProvider(DataLayerProvider):
    name = "akshare"

    def list_instruments(self) -> list[DataLayerInstrument]:
        ak = _akshare()
        frame = ak.stock_info_a_code_name()
        if frame is None or frame.empty:
            return []
        instruments: list[DataLayerInstrument] = []
        for _, row in frame.iterrows():
            code = str(_pick(row, ["code", "证券代码", "A股代码"])).zfill(6)
            exchange = _exchange_for(code)
            name = str(_pick(row, ["name", "证券简称", "A股简称", "股票简称"], code))
            instruments.append(
                DataLayerInstrument(
                    code=code,
                    symbol=f"{code}.{exchange}",
                    exchange=exchange,
                    name=name,
                    market=_market_for(exchange),
                    industry=str(_pick(row, ["industry", "所属行业", "行业"], "")),
                    list_date=_maybe_date(_pick(row, ["上市日期", "list_date"], None)),
                    delist_date=_maybe_date(_pick(row, ["退市日期", "delist_date"], None)),
                    status="active",
                )
            )
        return instruments

    def get_trading_calendar(self, start_date: date, end_date: date) -> list[DataLayerTradingDay]:
        ak = _akshare()
        frame = ak.tool_trade_date_hist_sina()
        if frame is None or frame.empty:
            return []
        days: list[DataLayerTradingDay] = []
        for _, row in frame.iterrows():
            trade_date = _to_date(_pick(row, ["trade_date", "日期", "calendarDate"]))
            if start_date <= trade_date <= end_date:
                days.append(DataLayerTradingDay(trade_date=trade_date, exchange="CN_A", is_open=True))
        return days

    def get_daily_bars(self, code: str, start_date: date, end_date: date, *, price_adjustment: str = "raw") -> list[DataLayerDailyBar]:
        ak = _akshare()
        normalized = str(code).zfill(6)
        adjustment = _normalize_price_adjustment(price_adjustment)
        try:
            frame = ak.stock_zh_a_hist(
                symbol=normalized,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="" if adjustment == "raw" else adjustment,
                timeout=30,
            )
        except Exception:
            frame = self._daily_bars_fallback_frame(ak, normalized, start_date, end_date, adjustment)
        if frame is None or frame.empty:
            return []
        exchange = _exchange_for(normalized)
        return [
            DataLayerDailyBar(
                code=normalized,
                symbol=f"{normalized}.{exchange}",
                exchange=exchange,
                trade_date=_to_date(_pick(row, ["日期", "date", "trade_date"])),
                open=_to_float(_pick(row, ["开盘", "open"])),
                high=_to_float(_pick(row, ["最高", "high"])),
                low=_to_float(_pick(row, ["最低", "low"])),
                close=_to_float(_pick(row, ["收盘", "close"])),
                volume=int(_to_float(_pick(row, ["成交量", "volume"], 0))),
                amount=_to_float(_pick(row, ["成交额", "amount"], 0)),
                price_adjustment=adjustment,
            )
            for _, row in frame.iterrows()
        ]

    def _daily_bars_fallback_frame(self, ak, code: str, start_date: date, end_date: date, adjustment: str):
        frame = ak.stock_zh_a_hist_tx(
            symbol=_prefixed_stock_symbol(code),
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="" if adjustment == "raw" else adjustment,
            timeout=30,
        )
        if frame is None or frame.empty:
            return frame
        frame = frame.copy()
        frame["日期"] = frame["date"]
        frame["开盘"] = frame["open"]
        frame["收盘"] = frame["close"]
        frame["最高"] = frame["high"]
        frame["最低"] = frame["low"]
        frame["成交量"] = frame["amount"].fillna(0)
        frame["成交额"] = frame["amount"].fillna(0) * frame["close"].fillna(0) * 100
        return frame

    def get_daily_bars_bulk(self, target_date: date, *, price_adjustment: str = "raw") -> list[DataLayerDailyBar] | None:
        adjustment = _normalize_price_adjustment(price_adjustment)
        if adjustment != "raw":
            return None
        ak = _akshare()
        frame = ak.stock_zh_a_spot_em()
        if frame is None or frame.empty:
            return []
        bars: list[DataLayerDailyBar] = []
        for _, row in frame.iterrows():
            code = str(_pick(row, ["代码", "code"], "")).zfill(6)
            if not code or not code.isdigit() or len(code) != 6:
                continue
            close = _to_float(_pick(row, ["最新价", "close"], 0))
            open_price = _to_float(_pick(row, ["今开", "open"], close))
            high = _to_float(_pick(row, ["最高", "high"], max(open_price, close)))
            low = _to_float(_pick(row, ["最低", "low"], min(open_price, close)))
            if close <= 0 or high < low:
                continue
            exchange = _exchange_for(code)
            bars.append(
                DataLayerDailyBar(
                    code=code,
                    symbol=f"{code}.{exchange}",
                    exchange=exchange,
                    trade_date=target_date,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=int(_to_float(_pick(row, ["成交量", "volume"], 0))),
                    amount=_to_float(_pick(row, ["成交额", "amount"], 0)),
                    price_adjustment="raw",
                )
            )
        return bars

    def get_index_daily_bars(self, index_code: str, start_date: date, end_date: date) -> list[DataLayerIndexDailyBar]:
        ak = _akshare()
        frame = self._index_daily_frame(ak, index_code, start_date, end_date)
        name = CORE_INDEXES.get(index_code, index_code)
        return [
            DataLayerIndexDailyBar(
                index_code=index_code,
                symbol=index_code,
                name=name,
                trade_date=_to_date(_pick(row, ["日期", "date", "trade_date"])),
                open=_to_float(_pick(row, ["开盘", "open"])),
                high=_to_float(_pick(row, ["最高", "high"])),
                low=_to_float(_pick(row, ["最低", "low"])),
                close=_to_float(_pick(row, ["收盘", "close"])),
                volume=int(_to_float(_pick(row, ["成交量", "volume"], 0))),
                amount=_to_float(_pick(row, ["成交额", "amount"], 0)),
            )
            for _, row in frame.iterrows()
        ]

    def _index_daily_frame(self, ak, index_code: str, start_date: date, end_date: date):
        em_symbol = _prefixed_index_symbol(index_code)
        compact_symbol = index_code.split(".")[0]
        start_text = start_date.strftime("%Y%m%d")
        end_text = end_date.strftime("%Y%m%d")

        errors: list[str] = []
        try:
            frame = ak.stock_zh_index_daily_em(symbol=em_symbol, start_date=start_text, end_date=end_text)
            if frame is not None and not frame.empty:
                return frame
        except Exception as exc:
            errors.append(f"stock_zh_index_daily_em={exc}")

        try:
            frame = ak.index_zh_a_hist(symbol=compact_symbol, period="daily", start_date=start_text, end_date=end_text)
            if frame is not None and not frame.empty:
                return frame
        except Exception as exc:
            errors.append(f"index_zh_a_hist={exc}")

        try:
            frame = ak.stock_zh_index_daily(symbol=em_symbol)
            if frame is not None and not frame.empty:
                filtered = []
                for _, row in frame.iterrows():
                    trade_date = _to_date(_pick(row, ["日期", "date", "trade_date"]))
                    if start_date <= trade_date <= end_date:
                        filtered.append(row)
                if filtered:
                    return type(frame)(filtered)
        except Exception as exc:
            errors.append(f"stock_zh_index_daily={exc}")

        if errors:
            raise RuntimeError("; ".join(errors))
        return []


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
    default_hosts = "push2.eastmoney.com,push2his.eastmoney.com,emappdata.eastmoney.com,*.eastmoney.com,eastmoney.com,qt.gtimg.cn,finance.pae.baidu.com,finance.sina.com.cn,*.sina.com.cn,proxy.finance.qq.com,*.qq.com"
    for key in ("NO_PROXY", "no_proxy"):
        current = os.getenv(key, "")
        values = [value.strip() for value in current.split(",") if value.strip()]
        for host in default_hosts.split(","):
            if host not in values:
                values.append(host)
        os.environ[key] = ",".join(values)


def _normalize_price_adjustment(price_adjustment: str) -> str:
    normalized = price_adjustment.strip().lower()
    if normalized in {"", "none", "raw"}:
        return "raw"
    if normalized in {"qfq", "hfq"}:
        return normalized
    raise ValueError(f"unsupported price adjustment: {price_adjustment}")


def _exchange_for(code: str) -> str:
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    return "SH"


def _market_for(exchange: str) -> str:
    return {"SH": "上证A股", "SZ": "深证A股", "BJ": "北京A股"}.get(exchange, "A股")


def _prefixed_index_symbol(index_code: str) -> str:
    code, _, exchange = index_code.partition(".")
    prefix = "sz" if exchange.upper() == "SZ" or code.startswith("399") else "sh"
    return f"{prefix}{code}"


def _prefixed_stock_symbol(code: str) -> str:
    return f"{'sh' if code.startswith('6') else 'sz'}{code}"


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


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _maybe_date(value: Any) -> date | None:
    if value in {None, ""}:
        return None
    try:
        return _to_date(value)
    except ValueError:
        return None
