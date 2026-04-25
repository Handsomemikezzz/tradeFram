from __future__ import annotations

from sqlalchemy.orm import Session

from . import models as m
from .database import Base, engine, SessionLocal
from .utils import new_id

STOCKS = [
    {
        "code": "600519",
        "symbol": "600519.SH",
        "exchange": "SH",
        "name": "贵州茅台",
        "price": 1650.50,
        "change": 12.30,
        "change_percent": 0.75,
        "volume": 12500,
        "amount": 2063000000,
        "market": "上证主板",
        "industry": "白酒",
        "pe": 28.5,
        "roe": 31.2,
        "revenue": "1500.20 亿",
        "profit": "740.10 亿",
        "gross_margin": 91.5,
        "net_margin": 49.3,
    },
    {
        "code": "000858",
        "symbol": "000858.SZ",
        "exchange": "SZ",
        "name": "五粮液",
        "price": 152.30,
        "change": -1.20,
        "change_percent": -0.78,
        "volume": 45000,
        "amount": 685000000,
        "market": "深证主板",
        "industry": "白酒",
        "pe": 18.2,
        "roe": 25.1,
        "revenue": "830.50 亿",
        "profit": "300.20 亿",
        "gross_margin": 75.2,
        "net_margin": 36.1,
    },
    {
        "code": "300750",
        "symbol": "300750.SZ",
        "exchange": "SZ",
        "name": "宁德时代",
        "price": 198.45,
        "change": 5.60,
        "change_percent": 2.90,
        "volume": 250000,
        "amount": 4960000000,
        "market": "创业板",
        "industry": "锂电池",
        "pe": 15.6,
        "roe": 22.4,
        "revenue": "4000.10 亿",
        "profit": "440.50 亿",
        "gross_margin": 20.2,
        "net_margin": 11.0,
    },
    {
        "code": "601318",
        "symbol": "601318.SH",
        "exchange": "SH",
        "name": "中国平安",
        "price": 45.30,
        "change": 0.10,
        "change_percent": 0.22,
        "volume": 800000,
        "amount": 3624000000,
        "market": "上证主板",
        "industry": "保险",
        "pe": 8.5,
        "roe": 12.1,
        "revenue": "12000.50 亿",
        "profit": "1000.20 亿",
        "gross_margin": 100.0,
        "net_margin": 8.3,
    },
]


def seed_database(db: Session | None = None) -> None:
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        for stock_data in STOCKS:
            if db.get(m.Stock, stock_data["code"]) is None:
                db.add(m.Stock(**stock_data))

        if db.get(m.PaperAccount, "paper_default") is None:
            db.add(m.PaperAccount(id="paper_default", initial_cash=1_000_000, cash=1_000_000))

        if db.get(m.PaperTradingEngineState, "default") is None:
            db.add(m.PaperTradingEngineState(id="default", active=False, mode="PAPER_TRADING_ONLY"))

        for source in [
            ("Tushare", "HEALTHY", 45),
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
                    event="Seed Data Ready",
                    detail="本地 SQLite mock 数据已初始化；仅支持 PAPER_TRADING_ONLY。",
                )
            )
        db.commit()
    finally:
        if owns_session:
            db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    seed_database()
