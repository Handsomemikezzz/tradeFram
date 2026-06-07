from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import models as m
from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.seed import seed_database
from tests.akshare_fixture import install_akshare_fixture, prepare_akshare_stock


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


def assert_ok(response):
    body = response.json()
    assert response.status_code == 200, body
    assert body["success"] is True, body
    return body["data"]


def assert_error(response, status_code: int, code: str):
    body = response.json()
    assert response.status_code == status_code, body
    assert body["success"] is False, body
    assert body["error"]["code"] == code, body


def _create_failed_task(code: str = "300750") -> str:
    with SessionLocal() as db:
        prepare_akshare_stock(db, code)
        task = m.ResearchTask(
            id="rt_failed_test",
            code=code,
            status="FAILED",
            current_step="RUN_TRADING_AGENTS",
            progress_pct=45,
            error_message="No module named 'yfinance'",
        )
        db.add(task)
        db.commit()
        return task.id


def _create_completed_task(code: str = "300750") -> tuple[str, str]:
    with SessionLocal() as db:
        prepare_akshare_stock(db, code)
        report = m.ResearchReport(
            id="rr_completed_test",
            task_id="rt_completed_test",
            code=code,
            status="COMPLETED",
            overview="测试报告",
            key_insights=["测试洞察"],
            risks=[],
            business_segments=[],
            news_items=[],
            worth_further_research=True,
            ai_confidence=0.8,
            data_completeness=0.9,
            ai_disclaimer="免责声明",
            research_base_period="2026-Q1",
            data_sources=["AkShare"],
        )
        task = m.ResearchTask(
            id="rt_completed_test",
            code=code,
            status="COMPLETED",
            current_step="DONE",
            progress_pct=100,
            report_id=report.id,
        )
        db.add(report)
        db.add(task)
        db.commit()
        return task.id, report.id


def test_delete_failed_research_task(monkeypatch):
    reset_database()
    install_akshare_fixture(monkeypatch)
    task_id = _create_failed_task()
    client = TestClient(app)

    assert_ok(client.delete(f"/api/v1/research/tasks/{task_id}"))

    records = assert_ok(client.get("/api/v1/research/records"))
    assert all(item["taskId"] != task_id for item in records["items"])


def test_delete_completed_research_task(monkeypatch):
    reset_database()
    install_akshare_fixture(monkeypatch)
    task_id, report_id = _create_completed_task()
    client = TestClient(app)

    assert_ok(client.delete(f"/api/v1/research/tasks/{task_id}"))

    records = assert_ok(client.get("/api/v1/research/records"))
    assert all(item["taskId"] != task_id for item in records["items"])

    with SessionLocal() as db:
        assert db.get(m.ResearchTask, task_id) is None
        assert db.get(m.ResearchReport, report_id) is None


def test_processing_research_task_cannot_be_deleted(monkeypatch):
    reset_database()
    install_akshare_fixture(monkeypatch)
    with SessionLocal() as db:
        prepare_akshare_stock(db, "300750")
        task = m.ResearchTask(
            id="rt_processing_test",
            code="300750",
            status="PROCESSING",
            current_step="RUN_TRADING_AGENTS",
            progress_pct=45,
        )
        db.add(task)
        db.commit()
    client = TestClient(app)

    assert_error(client.delete("/api/v1/research/tasks/rt_processing_test"), 400, "RESEARCH_TASK_NOT_DELETABLE")
