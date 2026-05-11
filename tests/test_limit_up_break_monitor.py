from __future__ import annotations

from datetime import UTC, date, datetime
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pandas as pd

from backend.app import models as m
from backend.app.data_layer.storage.parquet_store import ParquetStore
from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.seed import seed_database
from backend.app.services.limit_up_breaks import calculate_limit_up_price, resolve_default_limit_up_break_trade_date


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()
    os.environ["DATA_ROOT"] = tempfile.mkdtemp(prefix="waytofree-test-data-")


def assert_ok(response):
    body = response.json()
    assert response.status_code == 200, body
    assert body["success"] is True, body
    return body["data"]


def add_stock(code: str, name: str, *, market: str = "上证主板", exchange: str = "SH") -> None:
    add_instrument(code, name, market=market, exchange=exchange)
    with SessionLocal() as db:
        db.add(
            m.Stock(
                code=code,
                symbol=f"{code}.{exchange}",
                exchange=exchange,
                name=name,
                market=market,
                industry="测试",
            )
        )
        db.commit()


def add_instrument(code: str, name: str, *, market: str = "主板", exchange: str = "SH", industry: str = "测试") -> None:
    store = ParquetStore()
    path = Path(os.environ["DATA_ROOT"]) / "warehouse" / "instruments"
    rows = []
    if os.path.exists(path):
        rows = store.read_dataset(path).to_dict(orient="records")
    rows = [row for row in rows if str(row["code"]).zfill(6) != code]
    rows.append(
        {
            "code": code,
            "symbol": f"{code}.{exchange}",
            "exchange": exchange,
            "name": name,
            "market": market,
            "industry": industry,
            "list_date": None,
            "delist_date": None,
            "status": "active",
            "source_provider": "fake",
            "source_updated_at": datetime(2026, 5, 5, tzinfo=UTC),
        }
    )
    store.write_dataset(path, pd.DataFrame(rows), overwrite=True)


def add_bar(code: str, trade_date: date, close: float, *, amount: float = 10000, source: str = "AkShare", adjustment: str = "none") -> None:
    store = ParquetStore()
    path = Path(os.environ["DATA_ROOT"]) / "warehouse" / "daily_bars"
    rows = []
    if os.path.exists(path):
        rows = store.read_dataset(path).to_dict(orient="records")
    rows = [
        row
        for row in rows
        if not (
            str(row["code"]).zfill(6) == code
            and row["trade_date"] == trade_date
            and str(row.get("price_adjustment", "raw")) == _adjustment_name(adjustment)
        )
    ]
    rows.append(
        {
            "code": code,
            "symbol": f"{code}.SH" if code.startswith("6") else f"{code}.SZ",
            "exchange": "SH" if code.startswith("6") else "SZ",
            "trade_date": trade_date,
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1000,
            "amount": amount,
            "price_adjustment": _adjustment_name(adjustment),
            "source_provider": source,
            "source_updated_at": datetime(2026, 5, 5, tzinfo=UTC),
        }
    )
    store.write_dataset(path, pd.DataFrame(rows), partition_cols=["code"], overwrite=True)


def add_trading_calendar(days: list[tuple[date, bool]]) -> None:
    store = ParquetStore()
    path = Path(os.environ["DATA_ROOT"]) / "warehouse" / "trading_calendar"
    rows = [
        {
            "trade_date": trade_date,
            "exchange": "CN_A",
            "is_open": is_open,
            "source_provider": "fake",
            "source_updated_at": datetime(2026, 5, 10, tzinfo=UTC),
        }
        for trade_date, is_open in days
    ]
    store.write_dataset(path, pd.DataFrame(rows), overwrite=True)


def _adjustment_name(adjustment: str) -> str:
    return "raw" if adjustment in {"none", "raw"} else adjustment


def seed_two_board_candidate_then_break() -> None:
    add_stock("600001", "主板断板")
    add_stock("600002", "主板继续涨停")
    add_stock("600003", "主板停牌")
    add_stock("300001", "创业板排除", market="创业板", exchange="SZ")
    add_stock("600004", "ST排除")
    add_stock("600005", "交易日锚点")

    days = [date(2026, 4, 24), date(2026, 4, 27), date(2026, 4, 28), date(2026, 4, 29), date(2026, 4, 30)]
    for code in ["600001", "600002", "600003", "300001", "600004"]:
        add_bar(code, days[0], 10.0)
        add_bar(code, days[1], 11.0)
        add_bar(code, days[2], 12.1)
        add_bar(code, days[3], 13.31)
    for close_date, close in zip(days[:4], [10.0, 10.2, 10.3, 10.4], strict=True):
        add_bar("600005", close_date, close)

    add_bar("600001", days[4], 13.50, amount=26000)
    add_bar("600002", days[4], 14.64, amount=32000)
    add_bar("300001", days[4], 13.50)
    add_bar("600004", days[4], 13.50)
    add_bar("600005", days[4], 9.5)


def seed_two_board_candidate_then_break_in_warehouse() -> None:
    add_instrument("600001", "主板断板")
    add_instrument("600002", "主板继续涨停")
    add_instrument("600003", "主板停牌")
    add_instrument("300001", "创业板排除", market="创业板", exchange="SZ")
    add_instrument("600004", "ST排除")
    add_instrument("600005", "交易日锚点")

    days = [date(2026, 4, 24), date(2026, 4, 27), date(2026, 4, 28), date(2026, 4, 29), date(2026, 4, 30)]
    for code in ["600001", "600002", "600003", "300001", "600004"]:
        add_bar(code, days[0], 10.0)
        add_bar(code, days[1], 11.0)
        add_bar(code, days[2], 12.1)
        add_bar(code, days[3], 13.31)
    for close_date, close in zip(days[:4], [10.0, 10.2, 10.3, 10.4], strict=True):
        add_bar("600005", close_date, close)

    add_bar("600001", days[4], 13.50, amount=26000)
    add_bar("600002", days[4], 14.64, amount=32000)
    add_bar("300001", days[4], 13.50)
    add_bar("600004", days[4], 13.50)
    add_bar("600005", days[4], 9.5)


def add_full_coverage_anchor_stocks() -> None:
    days = [date(2026, 4, 24), date(2026, 4, 27), date(2026, 4, 28), date(2026, 4, 29), date(2026, 4, 30)]
    for index in range(6, 12):
        code = f"6000{index:02d}"
        add_stock(code, f"覆盖锚点{index}")
        for offset, trade_date in enumerate(days):
            add_bar(code, trade_date, 10.0 + offset / 10)


def test_main_board_limit_up_price_uses_exchange_rounding():
    assert calculate_limit_up_price(12.1) == 13.31
    assert calculate_limit_up_price(13.31) == 14.64


def test_generate_snapshot_finds_close_breaks_and_suspended_breaks():
    reset_database()
    seed_two_board_candidate_then_break()
    client = TestClient(app)

    snapshot = assert_ok(
        client.post(
            "/api/v1/limit-up-breaks/snapshots",
            json={"tradeDate": "2026-04-30", "threshold": 2, "provider": "AkShare"},
        )
    )

    assert snapshot["tradeDate"] == "2026-04-30"
    assert snapshot["threshold"] == 2
    assert snapshot["breakCount"] == 2
    assert snapshot["candidateCount"] == 3
    assert [item["code"] for item in snapshot["items"]] == ["600001", "600003"]
    assert snapshot["items"][0]["breakType"] == "CLOSE_NOT_LIMIT_UP"
    assert snapshot["items"][0]["previousLimitUpHeight"] == 3
    assert snapshot["items"][0]["changePercent"] == 1.43
    assert snapshot["items"][0]["amount"] == 26000
    assert snapshot["items"][0]["intradayBreak"] is None
    assert snapshot["items"][1]["breakType"] == "SUSPENDED"
    assert snapshot["items"][1]["changePercent"] is None


def test_generate_snapshot_rejects_low_target_date_data_coverage():
    reset_database()
    seed_two_board_candidate_then_break()
    add_stock("600006", "覆盖缺失样本")
    add_bar("600006", date(2026, 4, 29), 10.0)
    client = TestClient(app)

    response = client.post(
        "/api/v1/limit-up-breaks/snapshots",
        json={"tradeDate": "2026-04-30", "threshold": 2, "provider": "AkShare"},
    )
    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == "DATA_COVERAGE_TOO_LOW"
    assert "行情覆盖不足" in body["error"]["message"]


def test_generate_snapshot_uses_warehouse_instruments_without_sqlite_stocks():
    reset_database()
    seed_two_board_candidate_then_break_in_warehouse()
    client = TestClient(app)

    snapshot = assert_ok(client.post("/api/v1/limit-up-breaks/snapshots", json={"tradeDate": "2026-04-30"}))

    assert snapshot["candidateCount"] == 3
    assert [item["code"] for item in snapshot["items"]] == ["600001", "600003"]
    with SessionLocal() as db:
        assert db.query(m.Stock).count() == 0


def test_snapshot_generation_overwrites_same_day_threshold_and_provider():
    reset_database()
    seed_two_board_candidate_then_break()
    client = TestClient(app)
    first = assert_ok(client.post("/api/v1/limit-up-breaks/snapshots", json={"tradeDate": "2026-04-30"}))
    first_id = first["id"]

    add_bar("600001", date(2026, 4, 30), 14.64, amount=50000)
    second = assert_ok(client.post("/api/v1/limit-up-breaks/snapshots", json={"tradeDate": "2026-04-30"}))

    assert second["id"] == first_id
    assert second["breakCount"] == 1
    assert [item["code"] for item in second["items"]] == ["600003"]
    with SessionLocal() as db:
        assert db.query(m.LimitUpBreakSnapshot).count() == 1
        assert db.query(m.LimitUpBreakItem).count() == 1


def test_snapshot_can_be_queried_by_date():
    reset_database()
    seed_two_board_candidate_then_break()
    client = TestClient(app)
    assert_ok(client.post("/api/v1/limit-up-breaks/snapshots", json={"tradeDate": "2026-04-30"}))

    snapshot = assert_ok(client.get("/api/v1/limit-up-breaks/snapshots/2026-04-30?threshold=2&provider=AkShare"))

    assert snapshot["tradeDate"] == "2026-04-30"
    assert snapshot["breakCount"] == 2
    assert len(snapshot["items"]) == 2


def test_default_snapshot_query_reads_existing_snapshot_without_generation():
    reset_database()
    seed_two_board_candidate_then_break()
    add_trading_calendar(
        [
            (date(2026, 4, 29), True),
            (date(2026, 4, 30), True),
        ]
    )
    client = TestClient(app)
    created = assert_ok(client.post("/api/v1/limit-up-breaks/snapshots", json={"tradeDate": "2026-04-30"}))

    snapshot = assert_ok(client.get("/api/v1/limit-up-breaks/snapshots/default/latest?threshold=2&provider=AkShare"))

    assert snapshot["id"] == created["id"]
    assert snapshot["tradeDate"] == "2026-04-30"
    assert snapshot["breakCount"] == 2
    assert len(snapshot["items"]) == 2


CN_TZ = ZoneInfo("Asia/Shanghai")


def test_snapshot_query_does_not_fall_back_to_latest_available_trade_date():
    reset_database()
    seed_two_board_candidate_then_break()
    client = TestClient(app)
    assert_ok(client.post("/api/v1/limit-up-breaks/snapshots", json={"tradeDate": "2026-04-30", "provider": "akshare"}))

    response = client.get("/api/v1/limit-up-breaks/snapshots/2026-05-05?threshold=2&provider=AkShare")
    body = response.json()

    assert response.status_code == 404
    assert body["error"]["code"] == "LIMIT_UP_BREAK_SNAPSHOT_NOT_FOUND"


def test_snapshot_generation_does_not_fall_back_to_latest_available_trade_date():
    reset_database()
    seed_two_board_candidate_then_break()
    client = TestClient(app)

    response = client.post("/api/v1/limit-up-breaks/snapshots", json={"tradeDate": "2026-05-05", "provider": "AkShare"})
    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == "NO_PRICE_DATA"


def test_default_target_uses_previous_open_day_before_18_on_trading_day():
    reset_database()
    add_trading_calendar(
        [
            (date(2026, 5, 7), True),
            (date(2026, 5, 8), True),
        ]
    )

    target = resolve_default_limit_up_break_trade_date(now=datetime(2026, 5, 8, 17, 59, tzinfo=CN_TZ))

    assert target == date(2026, 5, 7)


def test_default_target_uses_today_after_18_on_trading_day():
    reset_database()
    add_trading_calendar(
        [
            (date(2026, 5, 7), True),
            (date(2026, 5, 8), True),
        ]
    )

    target = resolve_default_limit_up_break_trade_date(now=datetime(2026, 5, 8, 18, 0, tzinfo=CN_TZ))

    assert target == date(2026, 5, 8)


def test_default_target_uses_previous_open_day_on_weekend():
    reset_database()
    add_trading_calendar(
        [
            (date(2026, 5, 8), True),
            (date(2026, 5, 9), False),
            (date(2026, 5, 10), False),
        ]
    )

    target = resolve_default_limit_up_break_trade_date(now=datetime(2026, 5, 10, 10, 0, tzinfo=CN_TZ))

    assert target == date(2026, 5, 8)


def test_default_snapshot_does_not_fall_back_when_latest_target_data_is_incomplete():
    reset_database()
    seed_two_board_candidate_then_break()
    add_full_coverage_anchor_stocks()
    for code in ["600006", "600007", "600008", "600009", "600010"]:
        add_bar(code, date(2026, 5, 8), 10.5)
    add_trading_calendar(
        [
            (date(2026, 4, 30), True),
            (date(2026, 5, 8), True),
            (date(2026, 5, 9), False),
            (date(2026, 5, 10), False),
        ]
    )
    client = TestClient(app)

    response = client.post("/api/v1/limit-up-breaks/snapshots", json={"provider": "AkShare"})
    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == "DATA_COVERAGE_TOO_LOW"
    assert body["error"]["details"]["tradeDate"] == "2026-05-08"


def test_adjusted_price_bars_are_not_used_for_break_snapshots():
    reset_database()
    add_stock("600001", "前复权缓存")
    for trade_date, close in [(date(2026, 4, 27), 10.0), (date(2026, 4, 28), 11.0), (date(2026, 4, 29), 12.1), (date(2026, 4, 30), 11.5)]:
        add_bar("600001", trade_date, close, adjustment="qfq")
    client = TestClient(app)

    response = client.post("/api/v1/limit-up-breaks/snapshots", json={"tradeDate": "2026-04-30"})
    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == "NO_PRICE_DATA"
