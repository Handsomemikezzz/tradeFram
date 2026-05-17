from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app import models as m
from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.schemas import StockReviewCardClose, StockReviewCardCreate, StockReviewCardUpdate, StockReviewEventCreate
from backend.app.serializers_reviews import review_entry_payload, stock_review_card_payload, weekly_review_payload
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


def test_review_entry_and_weekly_payload_copy_lists():
    reset_database()
    with SessionLocal() as db:
        entry = m.ReviewEntry(
            id="rv_payload",
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
            id="wr_payload",
            week_start=date(2026, 5, 11),
            week_end=date(2026, 5, 17),
            summary_text="本周样本少",
            repeated_mistakes_text="无",
            effective_actions_text="轻仓",
            emotion_pattern_text="冷静",
            next_week_focus_text="继续观察",
            rule_candidates_text="计划外不交易",
            linked_entry_ids=["rv_payload"],
        )
        db.add(entry)
        db.add(weekly)
        db.commit()

        entry_payload = review_entry_payload(entry)
        weekly_payload = weekly_review_payload(weekly)

        entry_payload["sectorTags"].append("消费")
        entry_payload["emotionTags"].append("急躁")
        entry_payload["problemTags"].append("追高")
        weekly_payload["linkedEntryIds"].append("rv_other")

        assert entry.sector_tags == ["白酒"]
        assert entry.emotion_tags == ["冷静"]
        assert entry.problem_tags == ["无明显问题"]
        assert weekly.linked_entry_ids == ["rv_payload"]


def test_stock_review_card_models_can_persist_events():
    reset_database()
    with SessionLocal() as db:
        card = m.StockReviewCard(
            id="src_test",
            status="OPEN",
            code="600519",
            name="贵州茅台",
            sector_tags=["白酒"],
            start_date=date(2026, 5, 11),
            initial_action="BUY",
            initial_position_context="LIGHT",
            initial_plan_status="PLANNED",
            initial_reason_text="计划内买入",
            expected_move_text="趋势延续",
            original_plan_text="跌破五日线离场",
            initial_emotion_tags=["冷静"],
        )
        event = m.StockReviewEvent(
            id="sre_test",
            card_id="src_test",
            event_date=date(2026, 5, 12),
            event_type="HOLD",
            title="继续持有",
            reason_text="走势符合预期",
            position_snapshot="仍为轻仓",
            deviated_from_plan=False,
            emotion_tags=["冷静"],
            problem_tags=[],
        )
        db.add(card)
        db.add(event)
        db.commit()

        saved = db.get(m.StockReviewCard, "src_test")
        assert saved is not None
        assert saved.sector_tags == ["白酒"]
        assert saved.events[0].position_snapshot == "仍为轻仓"


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


def create_card(client: TestClient, **overrides):
    payload = {
        "code": "600519",
        "name": "贵州茅台",
        "sectorTags": ["白酒"],
        "startDate": "2026-05-11",
        "initialAction": "BUY",
        "initialPositionContext": "LIGHT",
        "initialPlanStatus": "PLANNED",
        "initialReasonText": "计划内买入",
        "expectedMoveText": "趋势延续",
        "originalPlanText": "跌破五日线离场",
        "initialEmotionTags": ["冷静"],
    }
    payload.update(overrides)
    return assert_ok(client.post("/api/v1/reviews/cards", json=payload))


def test_stock_review_card_lifecycle_and_summary():
    reset_database()
    client = TestClient(app)

    card = create_card(client)
    assert card["id"].startswith("src_")
    assert card["status"] == "OPEN"
    assert card["events"] == []

    event = assert_ok(
        client.post(
            f"/api/v1/reviews/cards/{card['id']}/events",
            json={
                "eventDate": "2026-05-12",
                "eventType": "HOLD",
                "title": "继续持有",
                "reasonText": "走势符合预期",
                "positionSnapshot": "仍为轻仓",
                "deviatedFromPlan": False,
                "emotionTags": ["冷静"],
                "problemTags": [],
            },
        )
    )
    assert event["eventType"] == "HOLD"

    detail = assert_ok(client.get(f"/api/v1/reviews/cards/{card['id']}"))
    assert len(detail["events"]) == 1
    assert detail["events"][0]["positionSnapshot"] == "仍为轻仓"

    closed = assert_ok(
        client.post(
            f"/api/v1/reviews/cards/{card['id']}/close",
            json={
                "endDate": "2026-05-13",
                "sellReasonText": "跌破计划线",
                "pnlText": "亏损 2%",
                "followedPlan": True,
                "disciplineScore": 4,
                "problemTags": ["判断问题"],
                "didWellText": "按计划止损",
                "didWrongText": "买点偏急",
                "reflectionText": "需要等确认",
                "ruleText": "跌破计划线直接走",
            },
        )
    )
    assert closed["status"] == "CLOSED"
    assert closed["endDate"] == "2026-05-13"
    assert closed["disciplineScore"] == 4

    repeated = client.post(
        f"/api/v1/reviews/cards/{card['id']}/close",
        json={
            "endDate": "2026-05-13",
            "sellReasonText": "再次结束",
            "pnlText": "亏损 2%",
            "followedPlan": True,
            "disciplineScore": 4,
            "problemTags": [],
            "didWellText": "按计划止损",
            "didWrongText": "买点偏急",
            "reflectionText": "需要等确认",
            "ruleText": "跌破计划线直接走",
        },
    )
    assert repeated.status_code == 400
    assert repeated.json()["error"]["code"] == "REVIEW_CARD_ALREADY_CLOSED"

    summary = assert_ok(
        client.get("/api/v1/reviews/cards/summary", params={"startDate": "2026-05-11", "endDate": "2026-05-17"})
    )
    assert summary["openCount"] == 0
    assert summary["closedCount"] == 1
    assert summary["createdInRangeCount"] == 1
    assert summary["closedInRangeCount"] == 1
    assert summary["lowDisciplineClosedCount"] == 0

    reopened = assert_ok(client.post(f"/api/v1/reviews/cards/{card['id']}/reopen"))
    assert reopened["status"] == "OPEN"
    assert reopened["sellReasonText"] == "跌破计划线"

    reopened_summary = assert_ok(
        client.get("/api/v1/reviews/cards/summary", params={"startDate": "2026-05-11", "endDate": "2026-05-17"})
    )
    assert reopened_summary["openCount"] == 1
    assert reopened_summary["closedCount"] == 0
    assert reopened_summary["closedInRangeCount"] == 0
    assert reopened_summary["lowDisciplineClosedCount"] == 0

    deleted = assert_ok(client.delete(f"/api/v1/reviews/cards/{card['id']}"))
    assert deleted["deleted"] is True

    missing = client.get(f"/api/v1/reviews/cards/{card['id']}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "REVIEW_CARD_NOT_FOUND"

    with SessionLocal() as db:
        assert db.get(m.StockReviewCard, card["id"]) is None
        assert db.get(m.StockReviewEvent, event["id"]) is None


def test_stock_review_card_create_requires_name_when_code_missing():
    try:
        StockReviewCardCreate(
            startDate="2026-05-11",
            initialAction="WATCH",
            initialPlanStatus="OBSERVED_ONLY",
            initialReasonText="观察板块机会",
            expectedMoveText="",
            originalPlanText="",
            sectorTags=["商业航天"],
            initialEmotionTags=[],
        )
    except ValidationError as exc:
        assert "code or name is required" in str(exc)
    else:
        raise AssertionError("StockReviewCardCreate accepted payload without code or name")


def test_stock_review_card_create_rejects_blank_identity_name():
    try:
        StockReviewCardCreate(
            name="   ",
            startDate="2026-05-11",
            initialAction="WATCH",
            initialPlanStatus="OBSERVED_ONLY",
            initialReasonText="观察板块机会",
            expectedMoveText="",
            originalPlanText="",
            sectorTags=["商业航天"],
            initialEmotionTags=[],
        )
    except ValidationError as exc:
        assert "code or name is required" in str(exc)
    else:
        raise AssertionError("StockReviewCardCreate accepted whitespace-only name without code")


def test_stock_review_card_update_normalizes_blank_identity_fields():
    update = StockReviewCardUpdate(code="   ", name="   ")

    assert update.code is None
    assert update.name is None


def test_stock_review_card_close_requires_discipline_score():
    try:
        StockReviewCardClose(
            endDate="2026-05-13",
            sellReasonText="跌破计划线",
            pnlText="小亏",
            followedPlan=True,
            didWellText="按计划离场",
            didWrongText="买点偏急",
            reflectionText="下次等确认",
            ruleText="跌破计划线直接走",
        )
    except ValidationError as exc:
        assert "disciplineScore" in str(exc)
    else:
        raise AssertionError("StockReviewCardClose accepted payload without disciplineScore")


def test_stock_review_event_create_rejects_invalid_type_and_blank_text():
    try:
        StockReviewEventCreate(
            eventDate="2026-05-12",
            eventType="INVALID",
            title="   ",
            reasonText="  ",
            positionSnapshot="仍为轻仓",
            deviatedFromPlan=False,
            emotionTags=[],
            problemTags=[],
        )
    except ValidationError as exc:
        error_text = str(exc)
        assert "eventType is invalid" in error_text
        assert "title" in error_text
        assert "reasonText" in error_text
    else:
        raise AssertionError("StockReviewEventCreate accepted invalid type and blank text")


def test_stock_review_card_close_rejects_blank_required_text():
    try:
        StockReviewCardClose(
            endDate="2026-05-13",
            sellReasonText="   ",
            pnlText="小亏",
            followedPlan=True,
            disciplineScore=4,
            didWellText="按计划离场",
            didWrongText="买点偏急",
            reflectionText="下次等确认",
            ruleText=" ",
        )
    except ValidationError as exc:
        error_text = str(exc)
        assert "sellReasonText" in error_text
        assert "ruleText" in error_text
    else:
        raise AssertionError("StockReviewCardClose accepted blank required text")


def test_stock_review_card_payload_includes_events_and_copies_lists():
    reset_database()
    with SessionLocal() as db:
        card = m.StockReviewCard(
            id="src_payload",
            status="OPEN",
            code="600519",
            name="贵州茅台",
            sector_tags=["白酒"],
            start_date=date(2026, 5, 11),
            initial_action="BUY",
            initial_position_context="LIGHT",
            initial_plan_status="PLANNED",
            initial_reason_text="计划内买入",
            expected_move_text="趋势延续",
            original_plan_text="跌破五日线离场",
            initial_emotion_tags=["冷静"],
            problem_tags=["无明显问题"],
        )
        event = m.StockReviewEvent(
            id="sre_payload",
            card_id="src_payload",
            event_date=date(2026, 5, 12),
            event_type="HOLD",
            title="继续持有",
            reason_text="走势符合预期",
            position_snapshot="仍为轻仓",
            deviated_from_plan=False,
            emotion_tags=["冷静"],
            problem_tags=[],
        )
        db.add(card)
        db.add(event)
        db.commit()
        db.refresh(card)

        payload = stock_review_card_payload(card, include_events=True)

        assert payload["sectorTags"] == ["白酒"]
        assert payload["initialEmotionTags"] == ["冷静"]
        assert payload["problemTags"] == ["无明显问题"]
        assert payload["startDate"] == "2026-05-11"
        assert payload["initialPlanStatus"] == "PLANNED"
        assert payload["events"][0]["cardId"] == "src_payload"
        assert payload["events"][0]["eventType"] == "HOLD"
        assert payload["events"][0]["emotionTags"] == ["冷静"]

        payload["sectorTags"].append("消费")
        assert card.sector_tags == ["白酒"]


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
