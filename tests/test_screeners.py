from __future__ import annotations

from datetime import UTC, date, datetime
import os
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient
import pandas as pd

from backend.app import models as m
from backend.app.data_layer.storage.parquet_store import ParquetStore
from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.seed import seed_database
from backend.app.services.stock_universe import is_main_board, is_st
from backend.app.data_layer.warehouse.reader import WarehouseInstrument


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()
    os.environ["DATA_ROOT"] = tempfile.mkdtemp(prefix="waytofree-screener-test-")


def assert_ok(response):
    body = response.json()
    assert response.status_code == 200, body
    assert body["success"] is True, body
    return body["data"]


def add_instrument(code: str, name: str, *, exchange: str = "SH", industry: str = "测试") -> None:
    store = ParquetStore()
    path = Path(os.environ["DATA_ROOT"]) / "warehouse" / "instruments"
    rows = store.read_dataset(path).to_dict(orient="records") if path.exists() else []
    rows = [row for row in rows if str(row["code"]).zfill(6) != code]
    rows.append(
        {
            "code": code,
            "symbol": f"{code}.{exchange}",
            "exchange": exchange,
            "name": name,
            "market": "主板",
            "industry": industry,
            "list_date": None,
            "delist_date": None,
            "status": "active",
            "source_provider": "fake",
            "source_updated_at": datetime(2026, 5, 5, tzinfo=UTC),
        }
    )
    store.write_dataset(path, pd.DataFrame(rows), overwrite=True)


def add_bar(
    code: str,
    trade_date: date,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    amount: float = 200_000_000,
) -> None:
    store = ParquetStore()
    path = Path(os.environ["DATA_ROOT"]) / "warehouse" / "daily_bars"
    rows = store.read_dataset(path).to_dict(orient="records") if path.exists() else []
    rows = [
        row
        for row in rows
        if not (str(row["code"]).zfill(6) == code and row["trade_date"] == trade_date)
    ]
    rows.append(
        {
            "code": code,
            "symbol": f"{code}.SH",
            "exchange": "SH",
            "trade_date": trade_date,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1_000_000,
            "amount": amount,
            "price_adjustment": "raw",
            "source": "AkShare",
            "fetched_at": datetime(2026, 5, 5, tzinfo=UTC),
        }
    )
    store.write_dataset(path, pd.DataFrame(rows), overwrite=True)


def seed_main_board_universe(target: date, count: int = 6) -> None:
    for index in range(count):
        code = f"60000{index + 1}"
        add_instrument(code, f"测试{index}")
        price = 10.0 - index * 0.1
        for offset in range(70):
            day = date.fromordinal(target.toordinal() - 69 + offset)
            add_bar(code, day, open_=price, high=price + 0.2, low=price - 0.2, close=price)


def test_main_board_filters():
    assert is_main_board(WarehouseInstrument("600001", "600001.SH", "SH", "A", "主板", "X", "active"))
    assert not is_main_board(WarehouseInstrument("300001", "300001.SZ", "SZ", "A", "创业板", "X", "active"))
    assert is_st(WarehouseInstrument("600002", "600002.SH", "SH", "*ST测试", "主板", "X", "active"))


def test_screener_snapshot_not_found():
    reset_database()
    client = TestClient(app)
    response = client.get("/api/v1/screeners/snapshots/2026-05-20", params={"strategyType": "pattern_a"})
    assert response.status_code == 404


def test_daily_bars_endpoint_default_lookback():
    reset_database()
    target = date(2026, 5, 20)
    add_instrument("600519", "贵州茅台")
    for offset in range(35):
        day = date.fromordinal(target.toordinal() - 34 + offset)
        price = 100 + offset * 0.1
        add_bar("600519", day, open_=price, high=price + 1, low=price - 1, close=price)
    client = TestClient(app)
    data = assert_ok(client.get("/api/v1/screeners/stocks/600519/daily-bars", params={"endDate": target.isoformat()}))
    assert len(data["bars"]) == 30
    assert data["bars"][-1]["ma5"] is not None


def test_generate_pattern_a_snapshot_and_detail():
    reset_database()
    target = date(2026, 5, 20)
    seed_main_board_universe(target)
    client = TestClient(app)
    snapshot = assert_ok(
        client.post(
            "/api/v1/screeners/snapshots",
            json={"tradeDate": target.isoformat(), "provider": "AkShare", "strategyType": "pattern_a"},
        )
    )
    assert snapshot["strategyType"] == "pattern_a"
    assert snapshot["scanCount"] >= 6

    fetched = assert_ok(client.get(f"/api/v1/screeners/snapshots/{target.isoformat()}", params={"strategyType": "pattern_a"}))
    assert fetched["id"] == snapshot["id"]

    if fetched["items"]:
        item = fetched["items"][0]
        detail = assert_ok(client.get(f"/api/v1/screeners/snapshots/{snapshot['id']}/items/{item['id']}"))
        assert len(detail["bars"]) == 30
        assert "markers" in detail


def test_daily_bars_rejects_lookback_over_120():
    reset_database()
    client = TestClient(app)
    response = client.get("/api/v1/screeners/stocks/600519/daily-bars", params={"lookback": 121})
    assert response.status_code == 422


def test_snapshot_upsert_keeps_same_id():
    reset_database()
    target = date(2026, 5, 20)
    seed_main_board_universe(target)
    client = TestClient(app)
    first = assert_ok(
        client.post(
            "/api/v1/screeners/snapshots",
            json={"tradeDate": target.isoformat(), "provider": "AkShare", "strategyType": "pattern_a"},
        )
    )
    second = assert_ok(
        client.post(
            "/api/v1/screeners/snapshots",
            json={"tradeDate": target.isoformat(), "provider": "AkShare", "strategyType": "pattern_a"},
        )
    )
    assert first["id"] == second["id"]


def test_in_watchlist_flag_on_snapshot_items():
    reset_database()
    target = date(2026, 5, 20)
    seed_main_board_universe(target, count=3)
    with SessionLocal() as db:
        db.add(
            m.Stock(
                code="600001",
                symbol="600001.SH",
                exchange="SH",
                name="测试0",
                market="主板",
                industry="测试",
            )
        )
        db.add(m.WatchlistItem(id="wl_test", code="600001", source="pattern_a"))
        db.commit()
    client = TestClient(app)
    snapshot = assert_ok(
        client.post(
            "/api/v1/screeners/snapshots",
            json={"tradeDate": target.isoformat(), "provider": "AkShare", "strategyType": "pattern_a"},
        )
    )
    watched = next((item for item in snapshot["items"] if item["code"] == "600001"), None)
    if watched is not None:
        assert watched["inWatchlist"] is True


def test_watchlist_ensure_stock_from_warehouse():
    reset_database()
    target = date(2026, 5, 20)
    add_instrument("600519", "贵州茅台")
    add_bar("600519", target, open_=100, high=101, low=99, close=100.5)
    client = TestClient(app)
    data = assert_ok(
        client.post(
            "/api/v1/watchlist/items",
            json={"code": "600519", "source": "pattern_a", "note": "走势 A"},
        )
    )
    assert data["code"] == "600519"
    with SessionLocal() as db:
        assert db.get(m.Stock, "600519") is not None
