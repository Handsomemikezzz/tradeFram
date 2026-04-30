from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str


@dataclass
class ValidationReport:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def error(self, code: str, message: str) -> None:
        self.errors.append(ValidationIssue(code=code, message=message, severity="error"))

    def warning(self, code: str, message: str) -> None:
        self.warnings.append(ValidationIssue(code=code, message=message, severity="warning"))


def validate_instruments(frame: pd.DataFrame) -> ValidationReport:
    report = ValidationReport()
    if frame.empty:
        report.error("EMPTY_INSTRUMENTS", "股票基础信息为空")
        return report
    if frame["code"].duplicated().any():
        report.error("DUPLICATE_INSTRUMENT", "同一股票代码出现重复基础信息")
    invalid_code = ~frame["code"].astype(str).str.fullmatch(r"\d{6}")
    if invalid_code.any():
        report.error("INVALID_CODE", "股票代码必须为 6 位数字")
    invalid_exchange = ~frame["exchange"].astype(str).isin(["SH", "SZ", "BJ"])
    if invalid_exchange.any():
        report.error("INVALID_EXCHANGE", "交易所必须为 SH/SZ/BJ")
    missing_name = frame["name"].isna() | (frame["name"].astype(str).str.strip() == "")
    if missing_name.any():
        report.error("MISSING_NAME", "股票名称不能为空")
    if "industry" in frame.columns:
        missing_industry = frame["industry"].isna() | (frame["industry"].astype(str).str.strip() == "")
        if missing_industry.any():
            report.warning("MISSING_INDUSTRY", "部分股票缺少行业字段")
    return report


def validate_trading_calendar(frame: pd.DataFrame) -> ValidationReport:
    report = ValidationReport()
    if frame.empty:
        report.error("EMPTY_TRADING_CALENDAR", "交易日历为空")
        return report
    if frame["trade_date"].duplicated().any():
        report.error("DUPLICATE_TRADING_DAY", "交易日历存在重复日期")
    if "is_open" in frame.columns and not frame["is_open"].map(lambda value: isinstance(value, bool)).all():
        report.error("INVALID_IS_OPEN", "is_open 必须为布尔值")
    if "is_open" in frame.columns and not frame["is_open"].any():
        report.error("NO_OPEN_TRADING_DAY", "日期范围内没有开市交易日")
    return report


def validate_daily_bars(frame: pd.DataFrame, *, expected_min_count_per_day: int | None = None) -> ValidationReport:
    report = _validate_bar_frame(frame, key_columns=["code", "trade_date", "price_adjustment"], duplicate_code="DUPLICATE_DAILY_BAR")
    if expected_min_count_per_day is not None and not frame.empty:
        counts = frame.groupby("trade_date")["code"].nunique()
        if (counts < expected_min_count_per_day).any():
            report.warning("LOW_DAILY_COUNT", "部分交易日股票数量低于预期")
    return report


def validate_index_daily_bars(frame: pd.DataFrame) -> ValidationReport:
    return _validate_bar_frame(frame, key_columns=["index_code", "trade_date"], duplicate_code="DUPLICATE_INDEX_BAR")


def _validate_bar_frame(frame: pd.DataFrame, *, key_columns: list[str], duplicate_code: str) -> ValidationReport:
    report = ValidationReport()
    if frame.empty:
        report.error("EMPTY_BARS", "行情数据为空")
        return report
    if frame.duplicated(subset=key_columns).any():
        report.error(duplicate_code, "行情数据存在重复键")
    required_price_cols = ["open", "high", "low", "close"]
    missing_price = frame[required_price_cols].isna().any(axis=1)
    if missing_price.any():
        report.error("MISSING_OHLC", "OHLC 字段不能为空")
    invalid_ohlc = (
        (frame["high"] < frame["low"])
        | (frame["high"] < frame["open"])
        | (frame["high"] < frame["close"])
        | (frame["low"] > frame["open"])
        | (frame["low"] > frame["close"])
    )
    if invalid_ohlc.any():
        report.error("INVALID_OHLC", "OHLC 高低价关系异常")
    if (frame["volume"] < 0).any():
        report.error("NEGATIVE_VOLUME", "成交量不能为负")
    if (frame["amount"] < 0).any():
        report.error("NEGATIVE_AMOUNT", "成交额不能为负")
    return report
