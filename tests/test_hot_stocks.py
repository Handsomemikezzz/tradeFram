from __future__ import annotations

from datetime import UTC, date, datetime
import os
from pathlib import Path
import tempfile

import pandas as pd
from fastapi.testclient import TestClient

from backend.app import models as m
from backend.app.data_layer.storage.parquet_store import ParquetStore
from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.seed import init_db


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_db()
    os.environ["DATA_ROOT"] = tempfile.mkdtemp(prefix="waytofree-hot-stocks-")


def assert_ok(response):
    body = response.json()
    assert response.status_code == 200, body
    assert body["success"] is True, body
    return body["data"]


def add_stock(code: str, name: str, *, industry: str = "测试行业", market: str = "上证主板", exchange: str = "SH") -> None:
    with SessionLocal() as db:
        existing = db.get(m.Stock, code)
        if existing:
            return
        db.add(
            m.Stock(
                code=code,
                symbol=f"{code}.{exchange}",
                exchange=exchange,
                name=name,
                market=market,
                industry=industry,
                price=10,
                change=0,
                change_percent=0,
                volume=0,
                amount=0,
                pe=0,
                roe=0,
                revenue="0 亿",
                profit="0 亿",
                gross_margin=0,
                net_margin=0,
            )
        )
        db.commit()
    add_instrument(code, name, industry=industry, market=market, exchange=exchange)


def add_instrument(code: str, name: str, *, industry: str = "测试行业", market: str = "上证主板", exchange: str = "SH") -> None:
    store = ParquetStore()
    path = Path(os.environ["DATA_ROOT"]) / "warehouse" / "instruments"
    rows = []
    if path.exists():
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
            "source_updated_at": datetime(2026, 6, 1, tzinfo=UTC),
        }
    )
    store.write_dataset(path, pd.DataFrame(rows), overwrite=True)


def add_bar(code: str, trade_date: date, close: float) -> None:
    store = ParquetStore()
    path = Path(os.environ["DATA_ROOT"]) / "warehouse" / "daily_bars"
    rows = []
    if path.exists():
        rows = store.read_dataset(path).to_dict(orient="records")
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
            "amount": 10000,
            "price_adjustment": "raw",
            "source_provider": "fake",
            "source_updated_at": datetime(2026, 6, 1, tzinfo=UTC),
        }
    )
    store.write_dataset(path, pd.DataFrame(rows), partition_cols=["code"], overwrite=True)


def test_hot_stock_models_persist_only_snapshot_fields():
    reset_database()
    add_stock("600001", "热点一")

    with SessionLocal() as db:
        snapshot = m.HotStockSnapshot(
            id="hs_1",
            trade_date=date(2026, 6, 1),
            source="EastmoneyHotRank",
            status="SUCCESS",
        )
        db.add(snapshot)
        db.add(
            m.HotStockItem(
                id="hsi_1",
                snapshot_id=snapshot.id,
                rank=1,
                code="600001",
                name="热点一",
                price=12.3,
                change_percent=4.56,
                industry="测试行业",
                ma5=11.0,
                ma20=10.5,
                trend_label="短期偏强",
                is_recent_limit_up_break=False,
            )
        )
        db.commit()

        item = db.query(m.HotStockItem).filter(m.HotStockItem.code == "600001").one()
        assert item.trend_label == "短期偏强"
        assert not hasattr(item, "in_watchlist")
        assert not hasattr(item, "has_open_review_card")
        assert not hasattr(item, "research_status")
        assert not hasattr(item, "deep_analysis_report_path")


def seed_hot_stock_inputs() -> None:
    add_stock("600001", "热点一", industry="电力")
    add_stock("600002", "热点二", industry="电子")
    for code in ["600001", "600002"]:
        for index, close in enumerate([10, 10.5, 11, 11.5, 12, 12.5], start=1):
            add_bar(code, date(2026, 5, index), close)


def fake_rank_rows():
    return [
        {"当前排名": 1, "代码": "600001", "股票名称": "热点一", "最新价": 12.3, "涨跌幅": 4.56},
        {"当前排名": 2, "代码": "600002", "股票名称": "热点二", "最新价": 8.9, "涨跌幅": -1.23},
    ]


def test_generate_hot_stock_snapshot_uses_rank_rows_and_indicators(monkeypatch):
    reset_database()
    seed_hot_stock_inputs()

    from backend.app.services import hot_stocks

    monkeypatch.setattr(
        hot_stocks,
        "_fetch_hot_rank",
        lambda limit: (fake_rank_rows()[:limit], hot_stocks.PRIMARY_HOT_RANK_SOURCE),
    )
    monkeypatch.setattr(hot_stocks, "_today", lambda: date(2026, 6, 1))

    with SessionLocal() as db:
        snapshot = hot_stocks.generate_hot_stock_snapshot(db, limit=20, force_refresh=True)
        db.commit()
        items = db.query(m.HotStockItem).filter(m.HotStockItem.snapshot_id == snapshot.id).order_by(m.HotStockItem.rank).all()

    assert snapshot.trade_date == date(2026, 6, 1)
    assert snapshot.status == "SUCCESS"
    assert [item.code for item in items] == ["600001", "600002"]
    assert items[0].industry == "电力"
    assert items[0].ma5 is not None
    assert items[0].ma20 is not None
    assert items[0].trend_label in {"短期偏强", "短期偏弱", "震荡"}


def test_generate_hot_stock_snapshot_reuses_today_success_without_refresh(monkeypatch):
    reset_database()
    seed_hot_stock_inputs()

    from backend.app.services import hot_stocks

    calls = {"count": 0}

    def fake_fetch(limit: int):
        calls["count"] += 1
        return fake_rank_rows()[:limit], hot_stocks.PRIMARY_HOT_RANK_SOURCE

    monkeypatch.setattr(hot_stocks, "_fetch_hot_rank", fake_fetch)
    monkeypatch.setattr(hot_stocks, "_today", lambda: date(2026, 6, 1))

    with SessionLocal() as db:
        first = hot_stocks.generate_hot_stock_snapshot(db, limit=20, force_refresh=False)
        second = hot_stocks.generate_hot_stock_snapshot(db, limit=20, force_refresh=False)

    assert first.id == second.id
    assert calls["count"] == 1


def test_latest_hot_stock_snapshot_falls_back_to_recent_success(monkeypatch):
    reset_database()
    seed_hot_stock_inputs()

    from backend.app.services import hot_stocks

    monkeypatch.setattr(
        hot_stocks,
        "_fetch_hot_rank",
        lambda limit: (fake_rank_rows()[:limit], hot_stocks.PRIMARY_HOT_RANK_SOURCE),
    )
    monkeypatch.setattr(hot_stocks, "_today", lambda: date(2026, 5, 31))
    with SessionLocal() as db:
        hot_stocks.generate_hot_stock_snapshot(db, limit=20, force_refresh=True)
        db.commit()

    monkeypatch.setattr(hot_stocks, "_today", lambda: date(2026, 6, 1))

    def fail_fetch(limit: int):
        raise RuntimeError("eastmoney unavailable")

    monkeypatch.setattr(hot_stocks, "_fetch_hot_rank", fail_fetch)

    with SessionLocal() as db:
        snapshot, is_fallback, error_message = hot_stocks.get_or_create_today_snapshot(
            db, limit=20, force_refresh=True
        )

    assert snapshot is not None
    assert snapshot.trade_date == date(2026, 5, 31)
    assert is_fallback is True
    assert "eastmoney unavailable" in (error_message or "")


def test_hot_stock_latest_response_derives_dynamic_workflow_state(monkeypatch):
    reset_database()
    seed_hot_stock_inputs()

    from backend.app.services import hot_stocks

    monkeypatch.setattr(
        hot_stocks,
        "_fetch_hot_rank",
        lambda limit: (fake_rank_rows()[:limit], hot_stocks.PRIMARY_HOT_RANK_SOURCE),
    )
    monkeypatch.setattr(hot_stocks, "_today", lambda: date(2026, 6, 1))

    with SessionLocal() as db:
        snapshot = hot_stocks.generate_hot_stock_snapshot(db, limit=20, force_refresh=True)
        db.add(m.WatchlistItem(id="wl_1", code="600001", source="USER"))
        db.add(
            m.StockReviewCard(
                id="src_1",
                status="OPEN",
                code="600001",
                name="热点一",
                start_date=date(2026, 6, 1),
                initial_action="WATCH",
                initial_plan_status="PLANNED",
                initial_reason_text="来自热门股观察",
            )
        )
        db.add(
            m.ResearchReport(
                id="rr_1",
                task_id="rt_1",
                code="600001",
                status="COMPLETED",
                overview="测试报告",
                key_insights=[],
                risks=[],
                business_segments=[],
                news_items=[],
                ai_disclaimer="测试",
            )
        )
        db.commit()
        assert snapshot.id

    client = TestClient(app)
    data = assert_ok(client.get("/api/v1/hot-stocks/latest"))
    first = data["items"][0]

    assert data["source"] == "EastmoneyHotRank"
    assert data["isFallback"] is False
    assert first["code"] == "600001"
    assert first["inWatchlist"] is True
    assert first["hasOpenReviewCard"] is True
    assert first["research"]["status"] == "HAS_REPORT"
    assert first["research"]["reportId"] == "rr_1"

    with SessionLocal() as db:
        db.query(m.WatchlistItem).filter(m.WatchlistItem.code == "600001").delete()
        db.commit()

    data_after_delete = assert_ok(client.get("/api/v1/hot-stocks/latest"))
    assert data_after_delete["items"][0]["inWatchlist"] is False


def test_hot_stock_summary_does_not_generate_external_snapshot(monkeypatch):
    reset_database()

    from backend.app.services import hot_stocks

    def fail_fetch(limit: int):
        raise AssertionError("summary must not call AkShare")

    monkeypatch.setattr(hot_stocks, "_fetch_hot_rank", fail_fetch)

    client = TestClient(app)
    data = assert_ok(client.get("/api/v1/hot-stocks/summary"))

    assert data["items"] == []
    assert data["errorMessage"] == "暂无热门股快照"


def test_hot_stock_summary_respects_limit(monkeypatch):
    reset_database()
    seed_hot_stock_inputs()

    from backend.app.services import hot_stocks

    monkeypatch.setattr(
        hot_stocks,
        "_fetch_hot_rank",
        lambda limit: (fake_rank_rows()[:limit], hot_stocks.PRIMARY_HOT_RANK_SOURCE),
    )
    monkeypatch.setattr(hot_stocks, "_today", lambda: date(2026, 6, 1))

    with SessionLocal() as db:
        hot_stocks.generate_hot_stock_snapshot(db, limit=20, force_refresh=True)
        db.commit()

    client = TestClient(app)
    data = assert_ok(client.get("/api/v1/hot-stocks/summary", params={"limit": 1}))
    assert len(data["items"]) == 1
    assert data["items"][0]["code"] == "600001"


def test_normalize_code_strips_exchange_prefix():
    from backend.app.services.hot_stocks import _normalize_code

    assert _normalize_code("SH603601") == "603601"
    assert _normalize_code("603601") == "603601"


def test_parse_tencent_quote_line_extracts_price_and_change():
    from backend.app.services.hot_stocks import _parse_tencent_quote_line

    parsed = _parse_tencent_quote_line('v_sh603890="1~春秋电子~603890~27.29~24.81~27.29~43261"')
    assert parsed == {
        "code": "603890",
        "name": "春秋电子",
        "price": 27.29,
        "change_percent": 10.0,
    }


def test_fetch_hot_rank_falls_back_to_baidu(monkeypatch):
    from backend.app.services import hot_stocks

    def fail_em(limit: int):
        raise RuntimeError("eastmoney down")

    def fail_ak(limit: int):
        raise RuntimeError("akshare down")

    monkeypatch.setattr(hot_stocks, "_fetch_eastmoney_hot_rank_emappdata", fail_em)
    monkeypatch.setattr(hot_stocks, "_fetch_eastmoney_hot_rank_akshare", fail_ak)
    monkeypatch.setattr(
        hot_stocks,
        "_fetch_baidu_hot_search",
        lambda limit: fake_rank_rows()[:limit],
    )

    rows, source = hot_stocks._fetch_hot_rank(2)
    assert source == hot_stocks.FALLBACK_HOT_RANK_SOURCE
    assert [row["代码"] for row in rows] == ["600001", "600002"]


def test_get_or_create_force_refresh_refetches_even_when_today_snapshot_exists(monkeypatch):
    reset_database()
    seed_hot_stock_inputs()

    from backend.app.services import hot_stocks

    calls = {"count": 0}

    def fake_fetch(limit: int):
        calls["count"] += 1
        rank = 1 if calls["count"] == 1 else 99
        return (
            [{"当前排名": rank, "代码": "600001", "股票名称": "热点一", "最新价": 12.3, "涨跌幅": 4.56}],
            hot_stocks.PRIMARY_HOT_RANK_SOURCE,
        )

    monkeypatch.setattr(hot_stocks, "_fetch_hot_rank", fake_fetch)
    monkeypatch.setattr(hot_stocks, "_today", lambda: date(2026, 6, 1))

    with SessionLocal() as db:
        first, _, _ = hot_stocks.get_or_create_today_snapshot(db, limit=1, force_refresh=True)
        second, _, _ = hot_stocks.get_or_create_today_snapshot(db, limit=1, force_refresh=True)
        db.commit()
        items = (
            db.query(m.HotStockItem)
            .filter(m.HotStockItem.snapshot_id == second.id)
            .order_by(m.HotStockItem.rank)
            .all()
        )

    assert first.id != second.id
    assert calls["count"] == 2
    assert items[0].rank == 99

