from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from ... import models as m
from ...database import SessionLocal
from ..storage.parquet_store import ParquetStore

PRICE_BAR_INSERT_CHUNK_SIZE = 50_000


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
            _replace_price_bars_from_warehouse(session, store.read_dataset(daily_path), provider_name)
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


def _replace_price_bars_from_warehouse(db: Session, daily: pd.DataFrame, provider_name: str) -> None:
    if daily.empty:
        return

    frame = daily.copy()
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    if "price_adjustment" not in frame.columns:
        frame["price_adjustment"] = "none"
    frame["price_adjustment"] = frame["price_adjustment"].fillna("none").astype(str)
    frame = frame[frame["price_adjustment"] == "none"]
    if frame.empty:
        return

    frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.date
    frame = frame.sort_values(["code", "trade_date"]).drop_duplicates(["code", "trade_date"], keep="last")

    db.execute(delete(m.PriceBar).where(m.PriceBar.source == provider_name))
    db.flush()

    fetched_at = datetime.now(UTC)
    for start in range(0, len(frame), PRICE_BAR_INSERT_CHUNK_SIZE):
        chunk = frame.iloc[start : start + PRICE_BAR_INSERT_CHUNK_SIZE]
        records = [
            {
                "id": _price_bar_id(provider_name, row.code, row.trade_date),
                "code": row.code,
                "trade_date": row.trade_date,
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": int(row.volume),
                "amount": float(row.amount),
                "source": provider_name,
                "price_adjustment": "none",
                "fetched_at": fetched_at,
            }
            for row in chunk.itertuples(index=False)
        ]
        db.execute(insert(m.PriceBar), records)
        db.flush()


def _price_bar_id(provider_name: str, code: str, trade_date) -> str:
    compact_provider = "".join(ch for ch in provider_name.lower() if ch.isalnum())[:16]
    return f"bar_{compact_provider}_{code}_{trade_date:%Y%m%d}"
