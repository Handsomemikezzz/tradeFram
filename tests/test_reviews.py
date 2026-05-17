from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from backend.app import models as m
from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.seed import seed_database


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


def assert_ok(response):
    body = response.json()
    assert response.status_code == 200, body
    assert body["success"] is True, body
    return body["data"]


def test_review_models_can_persist_json_tags():
    reset_database()
    with SessionLocal() as db:
        entry = m.ReviewEntry(
            id="rv_test",
            entry_type="TRADE_ACTION",
            action_type="BUY",
            trade_date=date(2026, 5, 11),
            code="600519",
            name="贵州茅台",
            sector_tags=["白酒"],
            position_context="LIGHT",
            plan_status="PLANNED",
            emotion_tags=["冷静"],
            problem_tags=["无明显问题"],
            reason_text="计划内观察后买入",
            reflection_text="执行符合计划",
            conclusion_text="计划内轻仓试错",
            next_action_text="继续只做计划内交易",
            discipline_score=5,
            outcome_text="待验证",
        )
        weekly = m.WeeklyReview(
            id="wr_test",
            week_start=date(2026, 5, 11),
            week_end=date(2026, 5, 17),
            summary_text="本周样本少",
            repeated_mistakes_text="无",
            effective_actions_text="轻仓",
            emotion_pattern_text="冷静",
            next_week_focus_text="继续观察",
            rule_candidates_text="计划外不交易",
            linked_entry_ids=["rv_test"],
        )
        db.add(entry)
        db.add(weekly)
        db.commit()

        saved = db.get(m.ReviewEntry, "rv_test")
        assert saved is not None
        assert saved.sector_tags == ["白酒"]
        assert saved.emotion_tags == ["冷静"]
        assert db.get(m.WeeklyReview, "wr_test").linked_entry_ids == ["rv_test"]
