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
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, default="strategy_ma_breakout")
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False, default="突破策略")
    strategy_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    risk_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="USER")
    report_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()


class LimitUpBreakSnapshot(Base):
    __tablename__ = "limit_up_break_snapshot"
    __table_args__ = (UniqueConstraint("trade_date", "threshold", "data_source", name="uq_limit_up_break_snapshot_date_threshold_source"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    previous_trade_date: Mapped[date | None] = mapped_column(Date)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    data_source: Mapped[str] = mapped_column(String(64), nullable=False, default="AkShare")
    price_adjustment: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    break_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suspended_break_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class LimitUpBreakItem(Base):
    __tablename__ = "limit_up_break_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), ForeignKey("limit_up_break_snapshot.id"), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_limit_up_height: Mapped[int] = mapped_column(Integer, nullable=False)
    change_percent: Mapped[float | None] = mapped_column(Float)
    amount: Mapped[float | None] = mapped_column(Float)
    intraday_break: Mapped[bool | None] = mapped_column(Boolean)
    break_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()
    snapshot: Mapped[LimitUpBreakSnapshot] = relationship()


class ScreenerSnapshot(Base):
    __tablename__ = "screener_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "strategy_type",
            "strategy_version",
            "provider",
            name="uq_screener_snapshot_date_strategy_provider",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    strategy_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="AkShare")
    price_adjustment: Mapped[str] = mapped_column(String(16), nullable=False, default="raw")
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    scan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confirmed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    items: Mapped[list["ScreenerItem"]] = relationship(back_populates="snapshot")


class ScreenerItem(Base):
    __tablename__ = "screener_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), ForeignKey("screener_snapshot.id"), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    industry: Mapped[str] = mapped_column(String(64), nullable=False, default="未知")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_action_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moving_average_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    volume_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    change_percent: Mapped[float | None] = mapped_column(Float)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reason: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    snapshot: Mapped[ScreenerSnapshot] = relationship(back_populates="items")


class HotStockSnapshot(Base):
    __tablename__ = "hot_stock_snapshot"
    __table_args__ = (
        UniqueConstraint("trade_date", "source", name="uq_hot_stock_snapshot_date_source"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="EastmoneyHotRank", index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="SUCCESS", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class HotStockItem(Base):
    __tablename__ = "hot_stock_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), ForeignKey("hot_stock_snapshot.id"), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(6), ForeignKey("stock.code"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[float | None] = mapped_column(Float)
    change_percent: Mapped[float | None] = mapped_column(Float)
    industry: Mapped[str | None] = mapped_column(String(64))
    ma5: Mapped[float | None] = mapped_column(Float)
    ma20: Mapped[float | None] = mapped_column(Float)
    trend_label: Mapped[str] = mapped_column(String(16), nullable=False, default="数据不足")
    is_recent_limit_up_break: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    stock: Mapped[Stock] = relationship()
    snapshot: Mapped[HotStockSnapshot] = relationship()


class ReviewEntry(Base):
    __tablename__ = "review_entry"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(6), index=True)
    name: Mapped[str | None] = mapped_column(String(64))
    sector_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    position_context: Mapped[str | None] = mapped_column(String(32))
    plan_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    emotion_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    problem_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    reflection_text: Mapped[str] = mapped_column(Text, nullable=False)
    conclusion_text: Mapped[str] = mapped_column(Text, nullable=False)
    next_action_text: Mapped[str] = mapped_column(Text, nullable=False)
    discipline_score: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class WeeklyReview(Base):
    __tablename__ = "weekly_review"
    __table_args__ = (UniqueConstraint("week_start", name="uq_weekly_review_week_start"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    repeated_mistakes_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    effective_actions_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    emotion_pattern_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    next_week_focus_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rule_candidates_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    linked_entry_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class StockReviewCard(Base):
    __tablename__ = "stock_review_cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN", index=True)
    code: Mapped[str | None] = mapped_column(String(6), index=True)
    name: Mapped[str | None] = mapped_column(String(64))
    sector_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)
    initial_action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    initial_position_context: Mapped[str | None] = mapped_column(String(32))
    initial_plan_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    initial_reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_move_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    original_plan_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    initial_emotion_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    problem_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sell_reason_text: Mapped[str | None] = mapped_column(Text)
    pnl_text: Mapped[str | None] = mapped_column(Text)
    followed_plan: Mapped[bool | None] = mapped_column(Boolean)
    discipline_score: Mapped[int | None] = mapped_column(Integer)
    did_well_text: Mapped[str | None] = mapped_column(Text)
    did_wrong_text: Mapped[str | None] = mapped_column(Text)
    reflection_text: Mapped[str | None] = mapped_column(Text)
    rule_text: Mapped[str | None] = mapped_column(Text)
    initial_images: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    close_images: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    
    # Professional Trading Audit Fields
    strategy_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_rr_ratio: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stop_loss_target: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pnl_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    r_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_regime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exit_quality: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    events: Mapped[list["StockReviewEvent"]] = relationship(
        "StockReviewEvent",
        back_populates="card",
        cascade="all, delete-orphan",
        order_by="StockReviewEvent.event_date.asc(), StockReviewEvent.created_at.asc()",
    )


class StockReviewEvent(Base):
    __tablename__ = "stock_review_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    card_id: Mapped[str] = mapped_column(
        ForeignKey("stock_review_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(96), nullable=False)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    position_snapshot: Mapped[str | None] = mapped_column(String(128))
    deviated_from_plan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    emotion_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    problem_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    images: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    card: Mapped[StockReviewCard] = relationship("StockReviewCard", back_populates="events")


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


class IronLaw(Base):
    __tablename__ = "iron_laws"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLIANT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
