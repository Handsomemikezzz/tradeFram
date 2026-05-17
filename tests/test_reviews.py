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


def test_create_review_entry_validates_type_and_stores_payload():
    reset_database()
    client = TestClient(app)

    data = assert_ok(
        client.post(
            "/api/v1/reviews/entries",
            json={
                "entryType": "TRADE_ACTION",
                "actionType": "BUY",
                "tradeDate": "2026-05-11",
                "code": "600519",
                "name": "贵州茅台",
                "sectorTags": ["白酒"],
                "positionContext": "LIGHT",
                "planStatus": "PLANNED",
                "emotionTags": ["冷静"],
                "problemTags": ["无明显问题"],
                "reasonText": "计划内轻仓试错",
                "reflectionText": "执行符合计划",
                "conclusionText": "计划内轻仓试错",
                "nextActionText": "只做计划内交易",
                "disciplineScore": 5,
                "outcomeText": "待验证",
            },
        )
    )

    assert data["id"].startswith("rv_")
    assert data["entryType"] == "TRADE_ACTION"
    assert data["actionType"] == "BUY"
    assert data["sectorTags"] == ["白酒"]
    assert data["disciplineScore"] == 5


def test_review_entry_rejects_invalid_action_for_entry_type():
    reset_database()
    client = TestClient(app)

    response = client.post(
        "/api/v1/reviews/entries",
        json={
            "entryType": "OBSERVATION_DECISION",
            "actionType": "BUY",
            "tradeDate": "2026-05-11",
            "planStatus": "OBSERVED_ONLY",
            "emotionTags": [],
            "problemTags": [],
            "reasonText": "想买",
            "reflectionText": "没买",
            "conclusionText": "观察",
            "nextActionText": "继续观察",
            "disciplineScore": 3,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def create_entry(client: TestClient, **overrides):
    payload = {
        "entryType": "TRADE_ACTION",
        "actionType": "BUY",
        "tradeDate": "2026-05-11",
        "code": "600519",
        "name": "贵州茅台",
        "sectorTags": ["白酒"],
        "positionContext": "LIGHT",
        "planStatus": "PLANNED",
        "emotionTags": ["冷静"],
        "problemTags": ["无明显问题"],
        "reasonText": "计划内轻仓试错",
        "reflectionText": "执行符合计划",
        "conclusionText": "计划内轻仓试错",
        "nextActionText": "只做计划内交易",
        "disciplineScore": 5,
        "outcomeText": "待验证",
    }
    payload.update(overrides)
    return assert_ok(client.post("/api/v1/reviews/entries", json=payload))


def test_review_entry_list_filters_and_stats_aggregate_tags():
    reset_database()
    client = TestClient(app)
    create_entry(client)
    create_entry(
        client,
        actionType="ADD",
        code="000001",
        name="平安银行",
        sectorTags=["银行"],
        planStatus="UNPLANNED",
        emotionTags=["怕踏空"],
        problemTags=["情绪问题", "仓位问题"],
        disciplineScore=2,
        conclusionText="计划外加仓",
    )

    page = assert_ok(client.get("/api/v1/reviews/entries", params={"emotionTags": ["怕踏空"]}))
    assert page["total"] == 1
    assert page["items"][0]["code"] == "000001"

    stats = assert_ok(client.get("/api/v1/reviews/stats", params={"startDate": "2026-05-11", "endDate": "2026-05-17"}))
    assert stats["totalCount"] == 2
    assert stats["tradeActionCount"] == 2
    assert stats["planStatusCounts"]["UNPLANNED"] == 1
    assert stats["emotionTagCounts"]["怕踏空"] == 1
    assert stats["problemTagCounts"]["仓位问题"] == 1
    assert stats["lowDisciplineCount"] == 1
    assert stats["lowDisciplineThreshold"] == 2


def test_weekly_workbench_requires_monday_and_saves_review():
    reset_database()
    client = TestClient(app)
    entry = create_entry(client, planStatus="UNPLANNED", emotionTags=["急躁"], problemTags=["执行问题"], disciplineScore=2)

    invalid = client.get("/api/v1/reviews/weeks/2026-05-12")
    assert invalid.status_code == 422

    workbench = assert_ok(client.get("/api/v1/reviews/weeks/2026-05-11"))
    assert workbench["weekStart"] == "2026-05-11"
    assert workbench["stats"]["totalCount"] == 1
    assert workbench["planDeviationEntries"][0]["id"] == entry["id"]
    assert workbench["lowDisciplineEntries"][0]["id"] == entry["id"]

    saved = assert_ok(
        client.put(
            "/api/v1/reviews/weeks/2026-05-11",
            json={
                "summaryText": "本周主要问题是急躁",
                "repeatedMistakesText": "计划外交易",
                "effectiveActionsText": "",
                "emotionPatternText": "急躁",
                "nextWeekFocusText": "只做计划内",
                "ruleCandidatesText": "计划外不加仓",
                "linkedEntryIds": [entry["id"]],
            },
        )
    )
    assert saved["summaryText"] == "本周主要问题是急躁"


def test_review_entry_validation_boundaries():
    reset_database()
    client = TestClient(app)
    response = client.post(
        "/api/v1/reviews/entries",
        json={
            "entryType": "TRADE_ACTION",
            "actionType": "BUY",
            "tradeDate": "2026-05-11",
            "planStatus": "PLANNED",
            "emotionTags": [],
            "problemTags": [],
            "reasonText": "计划内轻仓试错",
            "reflectionText": "执行符合计划",
            "conclusionText": "计划内轻仓试错",
            "nextActionText": "只做计划内交易",
            "disciplineScore": 6,
        },
    )
    assert response.status_code == 422

    created = create_entry(client)
    missing = client.put(
        "/api/v1/reviews/weeks/2026-05-11",
        json={
            "summaryText": "",
            "repeatedMistakesText": "",
            "effectiveActionsText": "",
            "emotionPatternText": "",
            "nextWeekFocusText": "",
            "ruleCandidatesText": "",
            "linkedEntryIds": [created["id"], "rv_missing"],
        },
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "REVIEW_ENTRY_NOT_FOUND"
