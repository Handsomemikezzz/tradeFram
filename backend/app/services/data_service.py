from __future__ import annotations

import os
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models as m
from ..providers.akshare_provider import AkShareMarketDataProvider
from ..providers.base import MarketDataProvider, ProviderDailyBar, ProviderFinancialSnapshot, ProviderStockProfile
from ..utils import dt_iso, new_id


class DataFetchError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 502, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def normalize_stock_code(raw_code: str) -> tuple[str, str, str]:
    raw = raw_code.strip().upper()
    match = re.fullmatch(r"(?:(SH|SZ|BJ))?(\d{6})(?:\.(SH|SZ|BJ))?", raw)
    if not match:
        raise ValueError("code must be a 6 digit A-share code, optionally with SH/SZ/BJ prefix or suffix")
    prefix, code, suffix = match.groups()
    exchange = suffix or prefix
    if exchange is None:
        if code.startswith("6"):
            exchange = "SH"
        elif code.startswith(("0", "3")):
            exchange = "SZ"
        elif code.startswith(("4", "8")):
            exchange = "BJ"
        else:
            exchange = "SH"
    return code, f"{code}.{exchange}", exchange


def cache_ttl_minutes() -> int:
    raw = os.getenv("DATA_CACHE_TTL_MINUTES", "1440")
    try:
        return max(int(raw), 0)
    except ValueError:
        return 1440


def get_provider(provider_name: str | None = None) -> MarketDataProvider:
    name = (provider_name or os.getenv("MARKET_DATA_PROVIDER") or "akshare").strip().lower()
    if name in {"akshare", "ak"}:
        return AkShareMarketDataProvider()
    raise DataFetchError("UNKNOWN_DATA_PROVIDER", f"未知数据源 {provider_name}", status_code=400)


def fetch_market_dataset(
    db: Session,
    raw_code: str,
    *,
    provider: MarketDataProvider | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    force_refresh: bool = False,
    allow_stale_on_error: bool = True,
) -> dict[str, Any]:
    code, _, _ = normalize_stock_code(raw_code)
    provider = provider or get_provider()
    end_date = end_date or date(2026, 4, 25)
    start_date = start_date or (end_date - timedelta(days=120))

    cached = _cached_dataset(db, code, provider.name)
    if cached is not None and not force_refresh and _is_cache_fresh(cached["latestFetchedAt"]):
        return cached | {
            "provider": provider.name,
            "dataSources": [provider.name, "Local Cache"],
            "usedCache": True,
            "dataStale": False,
            "refreshError": None,
        }

    log = m.DataFetchLog(id=new_id("fetch"), provider=provider.name, code=code, dataset="market_dataset", status="RUNNING")
    db.add(log)
    db.flush()

    try:
        profile = provider.get_stock_profile(code)
        if profile is None:
            raise DataFetchError("STOCK_NOT_FOUND", f"股票 {code} 基础信息不存在", status_code=404)
        bars = provider.get_daily_bars(code, start_date, end_date)
        if not bars:
            raise DataFetchError("NO_DAILY_DATA", f"股票 {code} 无可用日线行情数据", status_code=422)
        financial = _safe_financial(provider, code)
        calendar = _safe_calendar(provider, start_date, end_date)

        stock = _upsert_stock(db, profile, financial, bars[-1])
        _replace_price_bars(db, code, provider.name, bars)
        _insert_quote(db, stock, provider.name, bars)
        _upsert_financial(db, code, provider.name, financial)
        _upsert_calendar(db, provider.name, calendar)

        rows_fetched = len(bars) + len(calendar) + 1 + (1 if financial else 0)
        log.status = "SUCCESS"
        log.rows_fetched = rows_fetched
        log.finished_at = datetime.now(UTC)
        db.add(log)
        db.flush()

        return {
            "provider": provider.name,
            "stock": stock,
            "bars": bars,
            "financial": financial,
            "dataSources": [provider.name, "Provider Refresh"],
            "dataUpdatedAt": log.finished_at,
            "latestFetchedAt": log.finished_at,
            "dataCompleteness": _completeness(len(bars), financial is not None, False),
            "usedCache": False,
            "dataStale": False,
            "refreshError": None,
        }
    except DataFetchError as exc:
        _mark_fetch_failed(db, log, exc.message)
        stale = _cached_dataset(db, code, provider.name) if allow_stale_on_error else None
        if stale is not None:
            return stale | {
                "provider": provider.name,
                "dataSources": [provider.name, "Local Cache", "Stale Cache"],
                "usedCache": True,
                "dataStale": True,
                "refreshError": exc.message,
                "dataCompleteness": max(round(stale["dataCompleteness"] - 0.2, 2), 0.0),
            }
        raise
    except Exception as exc:
        _mark_fetch_failed(db, log, str(exc))
        stale = _cached_dataset(db, code, provider.name) if allow_stale_on_error else None
        if stale is not None:
            return stale | {
                "provider": provider.name,
                "dataSources": [provider.name, "Local Cache", "Stale Cache"],
                "usedCache": True,
                "dataStale": True,
                "refreshError": str(exc),
                "dataCompleteness": max(round(stale["dataCompleteness"] - 0.2, 2), 0.0),
            }
        raise DataFetchError("DATA_PROVIDER_ERROR", str(exc), status_code=502) from exc


def refresh_stock_data(db: Session, raw_code: str, provider_name: str | None = None) -> dict[str, Any]:
    provider = get_provider(provider_name)
    return fetch_market_dataset(db, raw_code, provider=provider, force_refresh=True, allow_stale_on_error=True)


def get_stock_data_status(db: Session, raw_code: str, provider_name: str | None = None) -> dict[str, Any]:
    code, symbol, exchange = normalize_stock_code(raw_code)
    provider = get_provider(provider_name) if provider_name else get_provider()
    latest_bar = (
        db.query(m.PriceBar)
        .filter(m.PriceBar.code == code, m.PriceBar.source == provider.name)
        .order_by(desc(m.PriceBar.trade_date))
        .first()
    )
    financial = (
        db.query(m.FinancialSnapshot)
        .filter(m.FinancialSnapshot.code == code, m.FinancialSnapshot.source == provider.name)
        .order_by(desc(m.FinancialSnapshot.fetched_at))
        .first()
    )
    latest_log = (
        db.query(m.DataFetchLog)
        .filter(m.DataFetchLog.code == code, m.DataFetchLog.provider == provider.name)
        .order_by(desc(m.DataFetchLog.started_at))
        .first()
    )
    bar_count = db.query(m.PriceBar).filter(m.PriceBar.code == code, m.PriceBar.source == provider.name).count()
    latest_fetched_at = latest_bar.fetched_at if latest_bar else None
    cache_fresh = _is_cache_fresh(latest_fetched_at) if latest_fetched_at else False
    has_cache = latest_bar is not None
    data_stale = has_cache and not cache_fresh
    data_completeness = _completeness(bar_count, financial is not None, data_stale) if has_cache else 0.0
    last_error = latest_log.error_message if latest_log and latest_log.status == "FAILED" else None
    return {
        "code": code,
        "symbol": symbol,
        "exchange": exchange,
        "provider": provider.name,
        "hasCache": has_cache,
        "priceBarCount": bar_count,
        "financialAvailable": financial is not None,
        "financialSnapshotAvailable": financial is not None,
        "latestTradeDate": latest_bar.trade_date.isoformat() if latest_bar else None,
        "lastFetchedAt": dt_iso(latest_fetched_at),
        "latestDataAt": dt_iso(latest_fetched_at),
        "cacheTtlMinutes": cache_ttl_minutes(),
        "cacheFresh": cache_fresh,
        "cacheHit": cache_fresh,
        "dataStale": data_stale,
        "dataCompleteness": data_completeness,
        "lastError": last_error,
        "lastFetchLog": fetch_log_payload(latest_log) if latest_log else None,
    }


def list_fetch_logs(db: Session, *, code: str | None = None, provider: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    normalized_code = normalize_stock_code(code)[0] if code else None
    query = db.query(m.DataFetchLog)
    if normalized_code:
        query = query.filter(m.DataFetchLog.code == normalized_code)
    if provider:
        query = query.filter(m.DataFetchLog.provider == provider)
    total = query.count()
    items = query.order_by(desc(m.DataFetchLog.started_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [fetch_log_payload(item) for item in items], "page": page, "pageSize": page_size, "total": total, "hasMore": page * page_size < total}


def fetch_log_payload(log: m.DataFetchLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "provider": log.provider,
        "code": log.code,
        "dataset": log.dataset,
        "status": log.status,
        "rowsFetched": log.rows_fetched,
        "errorMessage": log.error_message,
        "startedAt": dt_iso(log.started_at),
        "finishedAt": dt_iso(log.finished_at),
    }


def get_recent_price_bars(db: Session, code: str, limit: int = 60) -> list[m.PriceBar]:
    latest_success = (
        db.query(m.DataFetchLog)
        .filter(m.DataFetchLog.code == code, m.DataFetchLog.status == "SUCCESS")
        .order_by(desc(m.DataFetchLog.finished_at))
        .first()
    )
    query = db.query(m.PriceBar).filter(m.PriceBar.code == code)
    if latest_success is not None:
        query = query.filter(m.PriceBar.source == latest_success.provider)
    rows = query.order_by(desc(m.PriceBar.trade_date)).limit(limit).all()
    return list(reversed(rows))


def _cached_dataset(db: Session, code: str, source: str) -> dict[str, Any] | None:
    stock = db.get(m.Stock, code)
    if stock is None:
        return None
    bar_rows = (
        db.query(m.PriceBar)
        .filter(m.PriceBar.code == code, m.PriceBar.source == source)
        .order_by(desc(m.PriceBar.trade_date))
        .limit(120)
        .all()
    )
    if not bar_rows:
        return None
    bars = list(reversed(bar_rows))
    financial = (
        db.query(m.FinancialSnapshot)
        .filter(m.FinancialSnapshot.code == code, m.FinancialSnapshot.source == source)
        .order_by(desc(m.FinancialSnapshot.fetched_at))
        .first()
    )
    latest_fetched_at = max(bar.fetched_at for bar in bars)
    return {
        "stock": stock,
        "bars": bars,
        "financial": financial,
        "dataUpdatedAt": latest_fetched_at,
        "latestFetchedAt": latest_fetched_at,
        "dataCompleteness": _completeness(len(bars), financial is not None, False),
    }


def _is_cache_fresh(latest_fetched_at: datetime | None) -> bool:
    if latest_fetched_at is None:
        return False
    value = latest_fetched_at if latest_fetched_at.tzinfo else latest_fetched_at.replace(tzinfo=UTC)
    ttl = cache_ttl_minutes()
    return ttl > 0 and datetime.now(UTC) - value <= timedelta(minutes=ttl)


def _mark_fetch_failed(db: Session, log: m.DataFetchLog, message: str) -> None:
    log.status = "FAILED"
    log.error_message = message
    log.finished_at = datetime.now(UTC)
    db.add(log)
    db.commit()


def _safe_financial(provider: MarketDataProvider, code: str) -> ProviderFinancialSnapshot | None:
    try:
        return provider.get_financial_snapshot(code)
    except Exception:
        return None


def _safe_calendar(provider: MarketDataProvider, start_date: date, end_date: date):
    try:
        return provider.get_trading_calendar(start_date, end_date)
    except Exception:
        return []


def _upsert_stock(db: Session, profile: ProviderStockProfile, financial: ProviderFinancialSnapshot | None, latest_bar: ProviderDailyBar) -> m.Stock:
    stock = db.get(m.Stock, profile.code)
    prev = (
        db.query(m.PriceBar)
        .filter(m.PriceBar.code == profile.code, m.PriceBar.trade_date < latest_bar.trade_date)
        .order_by(desc(m.PriceBar.trade_date))
        .first()
    )
    change = round(latest_bar.close - prev.close, 2) if prev else 0.0
    change_percent = round((change / prev.close) * 100, 2) if prev and prev.close else 0.0
    if stock is None:
        stock = m.Stock(
            code=profile.code,
            symbol=profile.symbol,
            exchange=profile.exchange,
            name=profile.name,
            market=profile.market,
            industry=profile.industry,
        )
        db.add(stock)
    stock.symbol = profile.symbol
    stock.exchange = profile.exchange
    stock.name = profile.name
    stock.market = profile.market
    stock.industry = profile.industry
    stock.price = latest_bar.close
    stock.change = change
    stock.change_percent = change_percent
    stock.volume = latest_bar.volume
    stock.amount = latest_bar.amount
    if financial is not None:
        stock.pe = financial.pe
        stock.roe = financial.roe
        stock.revenue = financial.revenue
        stock.profit = financial.profit
        stock.gross_margin = financial.gross_margin
        stock.net_margin = financial.net_margin
    stock.update_time = datetime.now(UTC)
    db.flush()
    return stock


def _replace_price_bars(db: Session, code: str, source: str, bars: list[ProviderDailyBar]) -> None:
    db.query(m.PriceBar).filter(m.PriceBar.code == code, m.PriceBar.source == source).delete(synchronize_session=False)
    for bar in bars:
        db.add(
            m.PriceBar(
                id=new_id("bar"),
                code=code,
                trade_date=bar.trade_date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                amount=bar.amount,
                source=source,
            )
        )
    db.flush()


def _insert_quote(db: Session, stock: m.Stock, source: str, bars: list[ProviderDailyBar]) -> None:
    latest = bars[-1]
    db.add(
        m.MarketQuote(
            id=new_id("quote"),
            code=stock.code,
            symbol=stock.symbol,
            price=latest.close,
            change=stock.change,
            change_percent=stock.change_percent,
            volume=latest.volume,
            amount=latest.amount,
            source=source,
            quote_time=datetime.combine(latest.trade_date, datetime.min.time(), tzinfo=UTC),
        )
    )


def _upsert_financial(db: Session, code: str, source: str, financial: ProviderFinancialSnapshot | None) -> None:
    if financial is None:
        return
    db.query(m.FinancialSnapshot).filter(
        m.FinancialSnapshot.code == code,
        m.FinancialSnapshot.report_period == financial.report_period,
        m.FinancialSnapshot.source == source,
    ).delete(synchronize_session=False)
    db.add(
        m.FinancialSnapshot(
            id=new_id("fin"),
            code=code,
            report_period=financial.report_period,
            pe=financial.pe,
            roe=financial.roe,
            revenue=financial.revenue,
            profit=financial.profit,
            gross_margin=financial.gross_margin,
            net_margin=financial.net_margin,
            source=source,
        )
    )


def _upsert_calendar(db: Session, source: str, calendar) -> None:
    if not calendar:
        return
    for day in calendar:
        existing = (
            db.query(m.TradingCalendar)
            .filter(
                m.TradingCalendar.exchange == day.exchange,
                m.TradingCalendar.trade_date == day.trade_date,
                m.TradingCalendar.source == source,
            )
            .first()
        )
        if existing is None:
            db.add(m.TradingCalendar(id=new_id("cal"), exchange=day.exchange, trade_date=day.trade_date, is_open=day.is_open, source=source))
        else:
            existing.is_open = day.is_open
            existing.fetched_at = datetime.now(UTC)


def _completeness(bar_count: int, has_financial: bool, stale: bool) -> float:
    bar_score = min(bar_count / 60, 1.0) * 0.75
    financial_score = 0.2 if has_financial else 0.0
    profile_score = 0.05
    stale_penalty = 0.2 if stale else 0.0
    return max(round(bar_score + financial_score + profile_score - stale_penalty, 2), 0.0)
