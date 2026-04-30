from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ... import models as m
from ...database import SessionLocal
from ...utils import new_id
from ..storage.parquet_store import ParquetStore


def backfill_business_cache(*, data_root: Path, provider_name: str, db: Session | None = None) -> None:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        store = ParquetStore()
        instruments_path = data_root / "warehouse" / "instruments"
        daily_path = data_root / "warehouse" / "daily_bars"
        if instruments_path.exists():
            for row in store.read_dataset(instruments_path).to_dict(orient="records"):
                _upsert_stock(session, row)
        if daily_path.exists():
            for row in store.read_dataset(daily_path).to_dict(orient="records"):
                _upsert_price_bar(session, row, provider_name)
        session.commit()
    finally:
        if owns_session:
            session.close()


def _upsert_stock(db: Session, row: dict) -> None:
    stock = db.get(m.Stock, str(row["code"]).zfill(6))
    if stock is None:
        stock = m.Stock(code=str(row["code"]).zfill(6), symbol=str(row["symbol"]), exchange=str(row["exchange"]), name=str(row["name"]), market=str(row.get("market") or "A股"), industry=str(row.get("industry") or "UNKNOWN"))
        db.add(stock)
    else:
        stock.symbol = str(row["symbol"])
        stock.exchange = str(row["exchange"])
        stock.name = str(row["name"])
        stock.market = str(row.get("market") or stock.market)
        stock.industry = str(row.get("industry") or stock.industry)
    stock.update_time = datetime.now(UTC)


def _upsert_price_bar(db: Session, row: dict, provider_name: str) -> None:
    code = str(row["code"]).zfill(6)
    trade_date = row["trade_date"]
    existing = (
        db.query(m.PriceBar)
        .filter(m.PriceBar.code == code, m.PriceBar.trade_date == trade_date, m.PriceBar.source == provider_name)
        .first()
    )
    if existing is None:
        existing = m.PriceBar(id=new_id("bar"), code=code, trade_date=trade_date, source=provider_name)
        db.add(existing)
    existing.open = float(row["open"])
    existing.high = float(row["high"])
    existing.low = float(row["low"])
    existing.close = float(row["close"])
    existing.volume = int(row["volume"])
    existing.amount = float(row["amount"])
    existing.price_adjustment = str(row.get("price_adjustment") or "none")
    existing.fetched_at = datetime.now(UTC)
