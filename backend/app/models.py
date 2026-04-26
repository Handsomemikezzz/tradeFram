from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class Stock(Base):
    __tablename__ = "stock"

    code: Mapped[str] = mapped_column(String(6), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    exchange: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    industry: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    change: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    change_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    pe: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    roe: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    revenue: Mapped[str] = mapped_column(String(64), nullable=False, default="0 亿")
    profit: Mapped[str] = mapped_column(String(64), nullable=False, default="0 亿")
    gross_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    net_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class ResearchTask(Base):
    __tablename__ = "research_task"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PROCESSING")
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="IDENTIFY_STOCK")
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    report_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("research_report.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class ResearchReport(Base):
    __tablename__ = "research_report"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    key_insights: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    business_segments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    news_items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    worth_further_research: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.9)
    data_completeness: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    ai_disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    research_base_period: Mapped[str] = mapped_column(String(32), nullable=False, default="2026-Q1")
    data_sources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    stock: Mapped[Stock] = relationship()


class MarketQuote(Base):
    __tablename__ = "market_quote"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    change: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    change_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    quote_time: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class PriceBar(Base):
    __tablename__ = "price_bar"
    __table_args__ = (UniqueConstraint("code", "trade_date", "source", name="uq_price_bar_code_date_source"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshot"
    __table_args__ = (UniqueConstraint("code", "report_period", "source", name="uq_financial_snapshot_code_period_source"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    report_period: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    pe: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    roe: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    revenue: Mapped[str] = mapped_column(String(64), nullable=False, default="0 亿")
    profit: Mapped[str] = mapped_column(String(64), nullable=False, default="0 亿")
    gross_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    net_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class DataFetchLog(Base):
    __tablename__ = "data_fetch_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(6), index=True)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False, default="market_dataset")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    rows_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class TradingCalendar(Base):
    __tablename__ = "trading_calendar"
    __table_args__ = (UniqueConstraint("exchange", "trade_date", "source", name="uq_trading_calendar_exchange_date_source"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class WatchlistItem(Base):
    __tablename__ = "watchlist_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="USER")
    report_id: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class MonitoringItem(Base):
    __tablename__ = "monitoring_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, default="strategy_mock_breakout")
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False, default="突破策略")
    strategy_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    risk_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="USER")
    report_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class PaperTradingEngineState(Base):
    __tablename__ = "paper_trading_engine_state"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default="default")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="PAPER_TRADING_ONLY")
    polling_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    polling_interval_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    last_run_id: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class PaperTradingRun(Base):
    __tablename__ = "paper_trading_run"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING")
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class Signal(Base):
    __tablename__ = "signal"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_trading_run.id"), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    monitoring_item_id: Mapped[str] = mapped_column(String(64), ForeignKey("monitoring_item.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class RiskCheck(Base):
    __tablename__ = "risk_check"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_trading_run.id"), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signal_id: Mapped[str] = mapped_column(String(64), ForeignKey("signal.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    signal: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    rule: Mapped[str] = mapped_column(String(64), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class PaperOrder(Base):
    __tablename__ = "paper_order"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_trading_run.id"), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signal_id: Mapped[str] = mapped_column(String(64), ForeignKey("signal.id"), nullable=False)
    risk_check_id: Mapped[str] = mapped_column(String(64), ForeignKey("risk_check.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    raw_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    executed_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    slippage_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    commission: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    stamp_tax: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    estimated_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    final_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    net_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    filled_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    reject_reason: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class PaperExecution(Base):
    __tablename__ = "paper_execution"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_trading_run.id"), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_order.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False)
    filled_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    raw_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    executed_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    slippage_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    commission: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    stamp_tax: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    estimated_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    final_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    net_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class PaperAccount(Base):
    __tablename__ = "paper_account"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    initial_cash: Mapped[float] = mapped_column(Float, nullable=False, default=1_000_000)
    cash: Mapped[float] = mapped_column(Float, nullable=False, default=1_000_000)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class Position(Base):
    __tablename__ = "position"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_account.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    current_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    market_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    profit_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    last_run_id: Mapped[str | None] = mapped_column(String(64), index=True)
    last_trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class ExecutionTrace(Base):
    __tablename__ = "execution_trace"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_trading_run.id"), nullable=False, index=True)
    monitoring_item_id: Mapped[str] = mapped_column(String(64), ForeignKey("monitoring_item.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    current_step: Mapped[str] = mapped_column(String(32), nullable=False, default="SIGNAL")
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class SystemLog(Base):
    __tablename__ = "system_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str | None] = mapped_column(String(6), index=True)
    event: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    rel_id: Mapped[str | None] = mapped_column(String(64), index=True)
    run_id: Mapped[str | None] = mapped_column(String(64), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)


class DataSourceHealth(Base):
    __tablename__ = "data_source_health"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
