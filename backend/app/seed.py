from __future__ import annotations

from sqlalchemy.orm import Session

from . import models as m
from .database import Base, SessionLocal, engine
from .utils import new_id


def seed_database(db: Session | None = None) -> None:
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        if db.get(m.PaperAccount, "paper_default") is None:
            db.add(m.PaperAccount(id="paper_default", initial_cash=1_000_000, cash=1_000_000))

        if db.get(m.PaperTradingEngineState, "default") is None:
            db.add(m.PaperTradingEngineState(id="default", active=False, mode="PAPER_TRADING_ONLY"))

        for source in [
            ("AkShare", "HEALTHY", 120),
            ("AI Service", "HEALTHY", 1200),
            ("Local DB", "HEALTHY", 2),
        ]:
            if db.get(m.DataSourceHealth, source[0]) is None:
                db.add(m.DataSourceHealth(name=source[0], status=source[1], latency_ms=source[2]))

        if db.query(m.SystemLog).count() == 0:
            db.add(
                m.SystemLog(
                    id=new_id("log"),
                    level="INFO",
                    module="Seed",
                    event="System State Ready",
                    detail="本地 SQLite 系统状态已初始化；股票行情数据仅通过 AkShare 按需获取。",
                )
            )
        db.commit()
    finally:
        if owns_session:
            db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_lightweight_schema()
    seed_database()


def _ensure_lightweight_schema() -> None:
    """Small SQLite-friendly additive migration for local RC upgrades."""
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.begin() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(monitoring_item)").fetchall()}
        if "strategy_params" not in columns:
            conn.exec_driver_sql("ALTER TABLE monitoring_item ADD COLUMN strategy_params JSON NOT NULL DEFAULT '{}'")
        if "risk_params" not in columns:
            conn.exec_driver_sql("ALTER TABLE monitoring_item ADD COLUMN risk_params JSON NOT NULL DEFAULT '{}'")
        for table in ["paper_order", "paper_execution"]:
            table_columns = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
            for column in [
                "raw_price",
                "executed_price",
                "slippage_amount",
                "commission",
                "stamp_tax",
                "total_fee",
                "estimated_amount",
                "final_amount",
                "net_amount",
            ]:
                if column not in table_columns:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} FLOAT NOT NULL DEFAULT 0")
