# Trade Review Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manual trade review workbench that records trade actions and observation decisions, aggregates recurring mistakes, and supports weekly review summaries.

**Architecture:** Add two SQLAlchemy models and Alembic migration, expose deterministic FastAPI endpoints through a small review service/router layer, then add a React page split into focused review components. Keep v1 manual, non-AI, and non-advisory.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite JSON columns, Pytest, React, TypeScript, Vite, existing shadcn-style UI primitives, lucide-react.

---

## File Structure

- Modify `backend/app/models.py`: add `ReviewEntry` and `WeeklyReview`.
- Modify `backend/app/schemas.py`: add review request/response/query DTOs and validators.
- Create `backend/app/services/reviews.py`: create/update/delete entries, aggregate stats, build weekly workbench payloads.
- Create `backend/app/serializers_reviews.py`: serialize review models and aggregate data to camelCase API payloads.
- Create `backend/app/routers/reviews.py`: FastAPI endpoints under `/api/v1/reviews`.
- Modify `backend/app/main.py`: import and register the reviews router.
- Create `alembic/versions/20260517_0002_trade_review_workbench.py`: create `review_entries` and `weekly_reviews`.
- Create `tests/test_reviews.py`: API and service behavior coverage.
- Modify `src/services/api/client.ts`: add `put`.
- Modify `src/services/api/types.ts`: add review API types.
- Create `src/services/api/reviewApi.ts`: frontend review API wrapper.
- Modify `src/services/api/index.ts`: export `reviewApi`.
- Create `src/components/reviews/MultiTagInput.tsx`: reusable tag picker/input.
- Create `src/components/reviews/StatsOverview.tsx`: overview metrics and tag frequency display.
- Create `src/components/reviews/EntryForm.tsx`: create/edit form with placeholder guidance.
- Create `src/components/reviews/EntryList.tsx`: filterable list.
- Create `src/components/reviews/WeeklyWorkbench.tsx`: weekly aggregation and summary editor.
- Create `src/pages/Reviews.tsx`: page orchestration and data loading.
- Modify `src/App.tsx`: add `/reviews` route.
- Modify `src/components/layout/Sidebar.tsx`: add sidebar item.

## Constants

Use these values consistently across backend and frontend:

```python
ENTRY_TYPE_TRADE_ACTION = "TRADE_ACTION"
ENTRY_TYPE_OBSERVATION_DECISION = "OBSERVATION_DECISION"
TRADE_ACTIONS = {"BUY", "SELL", "ADD", "REDUCE", "CLEAR", "DO_T"}
OBSERVATION_ACTIONS = {"WANTED_BUY", "WANTED_SELL", "CANCELLED_ORDER", "HELD_BACK", "PLAN_OBSERVE"}
PLAN_STATUSES = {"PLANNED", "UNPLANNED", "INTRADAY_ADJUSTMENT", "OBSERVED_ONLY"}
LOW_DISCIPLINE_SCORE_THRESHOLD = 2
MAX_TAGS_PER_FIELD = 10
```

Frontend display labels:

```ts
export const reviewActionLabel: Record<string, string> = {
  BUY: '买入',
  SELL: '卖出',
  ADD: '加仓',
  REDUCE: '减仓',
  CLEAR: '清仓',
  DO_T: '做 T',
  WANTED_BUY: '想买未买',
  WANTED_SELL: '想卖未卖',
  CANCELLED_ORDER: '撤单',
  HELD_BACK: '忍住没动',
  PLAN_OBSERVE: '计划观察',
};
```

---

### Task 1: Backend Models And Migration

**Files:**
- Modify: `backend/app/models.py`
- Create: `alembic/versions/20260517_0002_trade_review_workbench.py`
- Test: `tests/test_reviews.py`

- [ ] **Step 1: Write failing model smoke test**

Add to `tests/test_reviews.py`:

```python
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
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
pytest tests/test_reviews.py::test_review_models_can_persist_json_tags -q
```

Expected: FAIL with `AttributeError: module 'backend.app.models' has no attribute 'ReviewEntry'`.

- [ ] **Step 3: Add models**

Append near other domain models in `backend/app/models.py`:

```python
class ReviewEntry(Base):
    __tablename__ = "review_entry"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(6), index=True)
    name: Mapped[str | None] = mapped_column(String(64))
    sector_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    position_context: Mapped[str | None] = mapped_column(String(32))
    plan_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    emotion_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    problem_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    reflection_text: Mapped[str] = mapped_column(Text, nullable=False)
    conclusion_text: Mapped[str] = mapped_column(Text, nullable=False)
    next_action_text: Mapped[str] = mapped_column(Text, nullable=False)
    discipline_score: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class WeeklyReview(Base):
    __tablename__ = "weekly_review"
    __table_args__ = (UniqueConstraint("week_start", name="uq_weekly_review_week_start"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    repeated_mistakes_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    effective_actions_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    emotion_pattern_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    next_week_focus_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rule_candidates_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    linked_entry_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
```

- [ ] **Step 4: Add migration**

Create `alembic/versions/20260517_0002_trade_review_workbench.py`:

```python
"""trade review workbench

Revision ID: 20260517_0002
Revises: 20260426_0001
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_0002"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_entry",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=True),
        sa.Column("sector_tags", sa.JSON(), nullable=False),
        sa.Column("position_context", sa.String(length=32), nullable=True),
        sa.Column("plan_status", sa.String(length=32), nullable=False),
        sa.Column("emotion_tags", sa.JSON(), nullable=False),
        sa.Column("problem_tags", sa.JSON(), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("reflection_text", sa.Text(), nullable=False),
        sa.Column("conclusion_text", sa.Text(), nullable=False),
        sa.Column("next_action_text", sa.Text(), nullable=False),
        sa.Column("discipline_score", sa.Integer(), nullable=False),
        sa.Column("outcome_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_entry_entry_type", "review_entry", ["entry_type"])
    op.create_index("ix_review_entry_action_type", "review_entry", ["action_type"])
    op.create_index("ix_review_entry_trade_date", "review_entry", ["trade_date"])
    op.create_index("ix_review_entry_code", "review_entry", ["code"])
    op.create_index("ix_review_entry_plan_status", "review_entry", ["plan_status"])

    op.create_table(
        "weekly_review",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("repeated_mistakes_text", sa.Text(), nullable=False),
        sa.Column("effective_actions_text", sa.Text(), nullable=False),
        sa.Column("emotion_pattern_text", sa.Text(), nullable=False),
        sa.Column("next_week_focus_text", sa.Text(), nullable=False),
        sa.Column("rule_candidates_text", sa.Text(), nullable=False),
        sa.Column("linked_entry_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_start", name="uq_weekly_review_week_start"),
    )
    op.create_index("ix_weekly_review_week_start", "weekly_review", ["week_start"])


def downgrade() -> None:
    op.drop_index("ix_weekly_review_week_start", table_name="weekly_review")
    op.drop_table("weekly_review")
    op.drop_index("ix_review_entry_plan_status", table_name="review_entry")
    op.drop_index("ix_review_entry_code", table_name="review_entry")
    op.drop_index("ix_review_entry_trade_date", table_name="review_entry")
    op.drop_index("ix_review_entry_action_type", table_name="review_entry")
    op.drop_index("ix_review_entry_entry_type", table_name="review_entry")
    op.drop_table("review_entry")
```

- [ ] **Step 5: Run model test**

Run:

```bash
pytest tests/test_reviews.py::test_review_models_can_persist_json_tags -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py alembic/versions/20260517_0002_trade_review_workbench.py tests/test_reviews.py
git commit -m "Add review persistence models"
```

---

### Task 2: Backend Schemas, Serializers, And Service

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/serializers_reviews.py`
- Create: `backend/app/services/reviews.py`
- Test: `tests/test_reviews.py`

- [ ] **Step 1: Add failing service/API-shape tests**

Append to `tests/test_reviews.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_reviews.py::test_create_review_entry_validates_type_and_stores_payload tests/test_reviews.py::test_review_entry_rejects_invalid_action_for_entry_type -q
```

Expected: FAIL with 404 for missing `/api/v1/reviews/entries`.

- [ ] **Step 3: Add schemas**

Add to `backend/app/schemas.py`:

```python
from datetime import timedelta

TRADE_ACTIONS = {"BUY", "SELL", "ADD", "REDUCE", "CLEAR", "DO_T"}
OBSERVATION_ACTIONS = {"WANTED_BUY", "WANTED_SELL", "CANCELLED_ORDER", "HELD_BACK", "PLAN_OBSERVE"}
PLAN_STATUSES = {"PLANNED", "UNPLANNED", "INTRADAY_ADJUSTMENT", "OBSERVED_ONLY"}
MAX_TAGS_PER_FIELD = 10


class ReviewEntryCreate(BaseModel):
    entryType: Literal["TRADE_ACTION", "OBSERVATION_DECISION"]
    actionType: str
    tradeDate: date
    code: str | None = Field(default=None, min_length=6, max_length=6)
    name: str | None = Field(default=None, max_length=64)
    sectorTags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_FIELD)
    positionContext: str | None = None
    planStatus: str
    emotionTags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_FIELD)
    problemTags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_FIELD)
    reasonText: str = Field(..., min_length=1)
    reflectionText: str = Field(..., min_length=1)
    conclusionText: str = Field(..., min_length=1)
    nextActionText: str = Field(..., min_length=1)
    disciplineScore: int = Field(..., ge=1, le=5)
    outcomeText: str | None = None

    @field_validator("tradeDate")
    @classmethod
    def trade_date_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("tradeDate cannot be in the future")
        return value

    @field_validator("planStatus")
    @classmethod
    def plan_status_valid(cls, value: str) -> str:
        if value not in PLAN_STATUSES:
            raise ValueError("planStatus is invalid")
        return value

    @field_validator("actionType")
    @classmethod
    def action_type_valid(cls, value: str, info) -> str:
        entry_type = info.data.get("entryType")
        allowed = TRADE_ACTIONS if entry_type == "TRADE_ACTION" else OBSERVATION_ACTIONS
        if value not in allowed:
            raise ValueError("actionType is invalid for entryType")
        return value


class ReviewEntryUpdate(BaseModel):
    entryType: Literal["TRADE_ACTION", "OBSERVATION_DECISION"] | None = None
    actionType: str | None = None
    tradeDate: date | None = None
    code: str | None = Field(default=None, min_length=6, max_length=6)
    name: str | None = Field(default=None, max_length=64)
    sectorTags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_FIELD)
    positionContext: str | None = None
    planStatus: str | None = None
    emotionTags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_FIELD)
    problemTags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_FIELD)
    reasonText: str | None = Field(default=None, min_length=1)
    reflectionText: str | None = Field(default=None, min_length=1)
    conclusionText: str | None = Field(default=None, min_length=1)
    nextActionText: str | None = Field(default=None, min_length=1)
    disciplineScore: int | None = Field(default=None, ge=1, le=5)
    outcomeText: str | None = None


class WeeklyReviewUpdate(BaseModel):
    summaryText: str = ""
    repeatedMistakesText: str = ""
    effectiveActionsText: str = ""
    emotionPatternText: str = ""
    nextWeekFocusText: str = ""
    ruleCandidatesText: str = ""
    linkedEntryIds: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Add serializers**

Create `backend/app/serializers_reviews.py`:

```python
from __future__ import annotations

from . import models as m


def review_entry_payload(entry: m.ReviewEntry) -> dict:
    return {
        "id": entry.id,
        "entryType": entry.entry_type,
        "actionType": entry.action_type,
        "tradeDate": entry.trade_date.isoformat(),
        "code": entry.code,
        "name": entry.name,
        "sectorTags": entry.sector_tags or [],
        "positionContext": entry.position_context,
        "planStatus": entry.plan_status,
        "emotionTags": entry.emotion_tags or [],
        "problemTags": entry.problem_tags or [],
        "reasonText": entry.reason_text,
        "reflectionText": entry.reflection_text,
        "conclusionText": entry.conclusion_text,
        "nextActionText": entry.next_action_text,
        "disciplineScore": entry.discipline_score,
        "outcomeText": entry.outcome_text,
        "createdAt": entry.created_at.isoformat(),
        "updatedAt": entry.updated_at.isoformat(),
    }


def weekly_review_payload(review: m.WeeklyReview | None) -> dict | None:
    if review is None:
        return None
    return {
        "id": review.id,
        "weekStart": review.week_start.isoformat(),
        "weekEnd": review.week_end.isoformat(),
        "summaryText": review.summary_text,
        "repeatedMistakesText": review.repeated_mistakes_text,
        "effectiveActionsText": review.effective_actions_text,
        "emotionPatternText": review.emotion_pattern_text,
        "nextWeekFocusText": review.next_week_focus_text,
        "ruleCandidatesText": review.rule_candidates_text,
        "linkedEntryIds": review.linked_entry_ids or [],
        "createdAt": review.created_at.isoformat(),
        "updatedAt": review.updated_at.isoformat(),
    }
```

- [ ] **Step 5: Add service create/update/delete primitives**

Create `backend/app/services/reviews.py`:

```python
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import ReviewEntryCreate, ReviewEntryUpdate, WeeklyReviewUpdate
from ..utils import api_error, new_id

LOW_DISCIPLINE_SCORE_THRESHOLD = 2


def _week_end(week_start: date) -> date:
    return week_start + timedelta(days=6)


def require_monday(value: date) -> None:
    if value.weekday() != 0:
        raise api_error(422, "INVALID_WEEK_START", "weekStart 必须是周一")


def create_review_entry(db: Session, payload: ReviewEntryCreate) -> m.ReviewEntry:
    entry = m.ReviewEntry(
        id=new_id("rv"),
        entry_type=payload.entryType,
        action_type=payload.actionType,
        trade_date=payload.tradeDate,
        code=payload.code,
        name=payload.name,
        sector_tags=payload.sectorTags,
        position_context=payload.positionContext,
        plan_status=payload.planStatus,
        emotion_tags=payload.emotionTags,
        problem_tags=payload.problemTags,
        reason_text=payload.reasonText,
        reflection_text=payload.reflectionText,
        conclusion_text=payload.conclusionText,
        next_action_text=payload.nextActionText,
        discipline_score=payload.disciplineScore,
        outcome_text=payload.outcomeText,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_review_entry_or_404(db: Session, entry_id: str) -> m.ReviewEntry:
    entry = db.get(m.ReviewEntry, entry_id)
    if entry is None:
        raise api_error(404, "REVIEW_ENTRY_NOT_FOUND", f"复盘记录 {entry_id} 不存在")
    return entry


def update_review_entry(db: Session, entry_id: str, payload: ReviewEntryUpdate) -> m.ReviewEntry:
    entry = get_review_entry_or_404(db, entry_id)
    data = payload.model_dump(exclude_unset=True)
    field_map = {
        "entryType": "entry_type",
        "actionType": "action_type",
        "tradeDate": "trade_date",
        "sectorTags": "sector_tags",
        "positionContext": "position_context",
        "planStatus": "plan_status",
        "emotionTags": "emotion_tags",
        "problemTags": "problem_tags",
        "reasonText": "reason_text",
        "reflectionText": "reflection_text",
        "conclusionText": "conclusion_text",
        "nextActionText": "next_action_text",
        "disciplineScore": "discipline_score",
        "outcomeText": "outcome_text",
    }
    for key, value in data.items():
        setattr(entry, field_map.get(key, key), value)
    entry.updated_at = m.now_utc()
    db.commit()
    db.refresh(entry)
    return entry


def delete_review_entry(db: Session, entry_id: str) -> None:
    entry = get_review_entry_or_404(db, entry_id)
    db.delete(entry)
    db.commit()
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_reviews.py::test_review_models_can_persist_json_tags -q
```

Expected: PASS. The API tests still fail until Task 3 registers router.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/serializers_reviews.py backend/app/services/reviews.py tests/test_reviews.py
git commit -m "Add review schemas and service primitives"
```

---

### Task 3: Backend Router, Listing, Stats, And Weekly Workbench

**Files:**
- Create: `backend/app/routers/reviews.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/reviews.py`
- Test: `tests/test_reviews.py`

- [ ] **Step 1: Add failing API tests for list, stats, weekly workbench**

Append to `tests/test_reviews.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_reviews.py -q
```

Expected: API tests fail with 404 until router exists.

- [ ] **Step 3: Complete service aggregations**

Append to `backend/app/services/reviews.py`:

```python
def list_review_entries(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    entry_type: str | None = None,
    action_type: str | None = None,
    code: str | None = None,
    plan_status: str | None = None,
    emotion_tags: list[str] | None = None,
    problem_tags: list[str] | None = None,
    sector_tags: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[m.ReviewEntry], int]:
    query = db.query(m.ReviewEntry)
    if start_date:
        query = query.filter(m.ReviewEntry.trade_date >= start_date)
    if end_date:
        query = query.filter(m.ReviewEntry.trade_date <= end_date)
    if entry_type:
        query = query.filter(m.ReviewEntry.entry_type == entry_type)
    if action_type:
        query = query.filter(m.ReviewEntry.action_type == action_type)
    if code:
        query = query.filter(m.ReviewEntry.code == code)
    if plan_status:
        query = query.filter(m.ReviewEntry.plan_status == plan_status)

    all_items = query.order_by(desc(m.ReviewEntry.trade_date), desc(m.ReviewEntry.created_at)).all()
    filtered = [
        item
        for item in all_items
        if _contains_all(item.emotion_tags or [], emotion_tags)
        and _contains_all(item.problem_tags or [], problem_tags)
        and _contains_all(item.sector_tags or [], sector_tags)
    ]
    total = len(filtered)
    start = (page - 1) * page_size
    return filtered[start : start + page_size], total


def _contains_all(values: list[str], required: list[str] | None) -> bool:
    if not required:
        return True
    value_set = set(values)
    return all(item in value_set for item in required)


def build_review_stats(entries: list[m.ReviewEntry], start_date: date, end_date: date) -> dict:
    plan_counts = Counter(entry.plan_status for entry in entries)
    emotion_counts = Counter(tag for entry in entries for tag in (entry.emotion_tags or []))
    problem_counts = Counter(tag for entry in entries for tag in (entry.problem_tags or []))
    sector_counts = Counter(tag for entry in entries for tag in (entry.sector_tags or []))
    code_counts = Counter(entry.code for entry in entries if entry.code)
    scores = [entry.discipline_score for entry in entries]
    unplanned = plan_counts.get("UNPLANNED", 0) + plan_counts.get("INTRADAY_ADJUSTMENT", 0)
    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "totalCount": len(entries),
        "tradeActionCount": sum(1 for entry in entries if entry.entry_type == "TRADE_ACTION"),
        "observationDecisionCount": sum(1 for entry in entries if entry.entry_type == "OBSERVATION_DECISION"),
        "planStatusCounts": dict(plan_counts),
        "emotionTagCounts": dict(emotion_counts),
        "problemTagCounts": dict(problem_counts),
        "sectorTagCounts": dict(sector_counts),
        "codeCounts": dict(code_counts),
        "averageDisciplineScore": round(sum(scores) / len(scores), 2) if scores else None,
        "lowDisciplineCount": sum(1 for score in scores if score <= LOW_DISCIPLINE_SCORE_THRESHOLD),
        "lowDisciplineThreshold": LOW_DISCIPLINE_SCORE_THRESHOLD,
        "planDeviationRatio": round(unplanned / len(entries), 4) if entries else 0,
    }


def get_stats_for_range(db: Session, start_date: date, end_date: date) -> dict:
    entries, _ = list_review_entries(db, start_date=start_date, end_date=end_date, page=1, page_size=10000)
    return build_review_stats(entries, start_date, end_date)


def get_weekly_workbench(db: Session, week_start: date) -> dict:
    require_monday(week_start)
    week_end = _week_end(week_start)
    entries, _ = list_review_entries(db, start_date=week_start, end_date=week_end, page=1, page_size=10000)
    review = db.query(m.WeeklyReview).filter(m.WeeklyReview.week_start == week_start).first()
    return {
        "weekStart": week_start.isoformat(),
        "weekEnd": week_end.isoformat(),
        "stats": build_review_stats(entries, week_start, week_end),
        "entries": entries,
        "planDeviationEntries": [entry for entry in entries if entry.plan_status in {"UNPLANNED", "INTRADAY_ADJUSTMENT"}],
        "lowDisciplineEntries": [entry for entry in entries if entry.discipline_score <= LOW_DISCIPLINE_SCORE_THRESHOLD],
        "weeklyReview": review,
    }


def save_weekly_review(db: Session, week_start: date, payload: WeeklyReviewUpdate) -> m.WeeklyReview:
    require_monday(week_start)
    missing = [entry_id for entry_id in payload.linkedEntryIds if db.get(m.ReviewEntry, entry_id) is None]
    if missing:
        raise api_error(422, "REVIEW_ENTRY_NOT_FOUND", "linkedEntryIds 包含不存在的复盘记录", {"missingIds": missing})
    review = db.query(m.WeeklyReview).filter(m.WeeklyReview.week_start == week_start).first()
    if review is None:
        review = m.WeeklyReview(id=new_id("wr"), week_start=week_start, week_end=_week_end(week_start))
        db.add(review)
    review.summary_text = payload.summaryText
    review.repeated_mistakes_text = payload.repeatedMistakesText
    review.effective_actions_text = payload.effectiveActionsText
    review.emotion_pattern_text = payload.emotionPatternText
    review.next_week_focus_text = payload.nextWeekFocusText
    review.rule_candidates_text = payload.ruleCandidatesText
    review.linked_entry_ids = payload.linkedEntryIds
    review.updated_at = m.now_utc()
    db.commit()
    db.refresh(review)
    return review
```

- [ ] **Step 4: Add router**

Create `backend/app/routers/reviews.py`:

```python
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ReviewEntryCreate, ReviewEntryUpdate, WeeklyReviewUpdate
from ..serializers_reviews import review_entry_payload, weekly_review_payload
from ..services.reviews import create_review_entry, delete_review_entry, get_review_entry_or_404, get_stats_for_range, get_weekly_workbench, list_review_entries, save_weekly_review, update_review_entry
from ..utils import ok

router = APIRouter()


@router.post("/reviews/entries")
def post_review_entry(payload: ReviewEntryCreate, db: Session = Depends(get_db)):
    return ok(review_entry_payload(create_review_entry(db, payload)))


@router.get("/reviews/entries")
def get_review_entries(
    startDate: date | None = None,
    endDate: date | None = None,
    entryType: str | None = None,
    actionType: str | None = None,
    code: str | None = None,
    planStatus: str | None = None,
    emotionTags: list[str] | None = Query(default=None),
    problemTags: list[str] | None = Query(default=None),
    sectorTags: list[str] | None = Query(default=None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = list_review_entries(
        db,
        start_date=startDate,
        end_date=endDate,
        entry_type=entryType,
        action_type=actionType,
        code=code,
        plan_status=planStatus,
        emotion_tags=emotionTags,
        problem_tags=problemTags,
        sector_tags=sectorTags,
        page=page,
        page_size=pageSize,
    )
    return ok({"items": [review_entry_payload(item) for item in items], "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})


@router.get("/reviews/entries/{entry_id}")
def get_review_entry(entry_id: str, db: Session = Depends(get_db)):
    return ok(review_entry_payload(get_review_entry_or_404(db, entry_id)))


@router.patch("/reviews/entries/{entry_id}")
def patch_review_entry(entry_id: str, payload: ReviewEntryUpdate, db: Session = Depends(get_db)):
    return ok(review_entry_payload(update_review_entry(db, entry_id, payload)))


@router.delete("/reviews/entries/{entry_id}")
def remove_review_entry(entry_id: str, db: Session = Depends(get_db)):
    delete_review_entry(db, entry_id)
    return ok({"deleted": True})


@router.get("/reviews/stats")
def get_review_stats(startDate: date, endDate: date, db: Session = Depends(get_db)):
    return ok(get_stats_for_range(db, startDate, endDate))


@router.get("/reviews/weeks/{week_start}")
def get_review_week(week_start: date, db: Session = Depends(get_db)):
    workbench = get_weekly_workbench(db, week_start)
    return ok(
        {
            **workbench,
            "entries": [review_entry_payload(entry) for entry in workbench["entries"]],
            "planDeviationEntries": [review_entry_payload(entry) for entry in workbench["planDeviationEntries"]],
            "lowDisciplineEntries": [review_entry_payload(entry) for entry in workbench["lowDisciplineEntries"]],
            "weeklyReview": weekly_review_payload(workbench["weeklyReview"]),
        }
    )


@router.put("/reviews/weeks/{week_start}")
def put_review_week(week_start: date, payload: WeeklyReviewUpdate, db: Session = Depends(get_db)):
    return ok(weekly_review_payload(save_weekly_review(db, week_start, payload)))
```

- [ ] **Step 5: Register router**

Modify `backend/app/main.py` imports:

```python
from .routers import audit, data, data_health, limit_up_breaks, monitoring, p0b, portfolio, research, reviews, system, trading
```

Modify router list:

```python
for router in [system.router, data.router, data_health.router, research.router, reviews.router, monitoring.router, limit_up_breaks.router, trading.router, portfolio.router, audit.router, p0b.router]:
    app.include_router(router, prefix="/api/v1")
```

- [ ] **Step 6: Run backend review tests**

Run:

```bash
pytest tests/test_reviews.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/reviews.py backend/app/main.py backend/app/services/reviews.py tests/test_reviews.py
git commit -m "Add review API and weekly aggregation"
```

---

### Task 4: Frontend API Types And Client

**Files:**
- Modify: `src/services/api/client.ts`
- Modify: `src/services/api/types.ts`
- Create: `src/services/api/reviewApi.ts`
- Modify: `src/services/api/index.ts`

- [ ] **Step 1: Add `put` method**

Modify `src/services/api/client.ts`:

```ts
export const apiClient = {
  get: <T>(path: string, query?: QueryParams) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown, query?: QueryParams) => request<T>('POST', path, { body, query }),
  put: <T>(path: string, body?: unknown, query?: QueryParams) => request<T>('PUT', path, { body, query }),
  patch: <T>(path: string, body?: unknown, query?: QueryParams) => request<T>('PATCH', path, { body, query }),
  delete: <T>(path: string, query?: QueryParams) => request<T>('DELETE', path, { query }),
};
```

- [ ] **Step 2: Add types**

Append to `src/services/api/types.ts`:

```ts
export type ReviewEntryType = 'TRADE_ACTION' | 'OBSERVATION_DECISION';
export type ReviewPlanStatus = 'PLANNED' | 'UNPLANNED' | 'INTRADAY_ADJUSTMENT' | 'OBSERVED_ONLY';

export interface ReviewEntryResponse {
  id: string;
  entryType: ReviewEntryType;
  actionType: string;
  tradeDate: string;
  code: string | null;
  name: string | null;
  sectorTags: string[];
  positionContext: string | null;
  planStatus: ReviewPlanStatus;
  emotionTags: string[];
  problemTags: string[];
  reasonText: string;
  reflectionText: string;
  conclusionText: string;
  nextActionText: string;
  disciplineScore: number;
  outcomeText: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ReviewEntryRequest {
  entryType: ReviewEntryType;
  actionType: string;
  tradeDate: string;
  code?: string | null;
  name?: string | null;
  sectorTags: string[];
  positionContext?: string | null;
  planStatus: ReviewPlanStatus;
  emotionTags: string[];
  problemTags: string[];
  reasonText: string;
  reflectionText: string;
  conclusionText: string;
  nextActionText: string;
  disciplineScore: number;
  outcomeText?: string | null;
}

export interface ReviewStatsResponse {
  startDate: string;
  endDate: string;
  totalCount: number;
  tradeActionCount: number;
  observationDecisionCount: number;
  planStatusCounts: Record<string, number>;
  emotionTagCounts: Record<string, number>;
  problemTagCounts: Record<string, number>;
  sectorTagCounts: Record<string, number>;
  codeCounts: Record<string, number>;
  averageDisciplineScore: number | null;
  lowDisciplineCount: number;
  lowDisciplineThreshold: number;
  planDeviationRatio: number;
}

export interface WeeklyReviewResponse {
  id: string;
  weekStart: string;
  weekEnd: string;
  summaryText: string;
  repeatedMistakesText: string;
  effectiveActionsText: string;
  emotionPatternText: string;
  nextWeekFocusText: string;
  ruleCandidatesText: string;
  linkedEntryIds: string[];
  createdAt: string;
  updatedAt: string;
}

export interface WeeklyWorkbenchResponse {
  weekStart: string;
  weekEnd: string;
  stats: ReviewStatsResponse;
  entries: ReviewEntryResponse[];
  planDeviationEntries: ReviewEntryResponse[];
  lowDisciplineEntries: ReviewEntryResponse[];
  weeklyReview: WeeklyReviewResponse | null;
}
```

- [ ] **Step 3: Add review API**

Create `src/services/api/reviewApi.ts`:

```ts
import { apiClient, QueryParams } from './client';
import { PageResponse, ReviewEntryRequest, ReviewEntryResponse, ReviewStatsResponse, WeeklyReviewResponse, WeeklyWorkbenchResponse } from './types';

export const reviewApi = {
  createEntry: (body: ReviewEntryRequest) => apiClient.post<ReviewEntryResponse>('/reviews/entries', body),
  getEntries: (query?: QueryParams) => apiClient.get<PageResponse<ReviewEntryResponse>>('/reviews/entries', query),
  getEntry: (id: string) => apiClient.get<ReviewEntryResponse>(`/reviews/entries/${id}`),
  updateEntry: (id: string, body: Partial<ReviewEntryRequest>) => apiClient.patch<ReviewEntryResponse>(`/reviews/entries/${id}`, body),
  deleteEntry: (id: string) => apiClient.delete<{ deleted: boolean }>(`/reviews/entries/${id}`),
  getStats: (query: { startDate: string; endDate: string }) => apiClient.get<ReviewStatsResponse>('/reviews/stats', query),
  getWeek: (weekStart: string) => apiClient.get<WeeklyWorkbenchResponse>(`/reviews/weeks/${weekStart}`),
  saveWeek: (weekStart: string, body: Omit<WeeklyReviewResponse, 'id' | 'weekStart' | 'weekEnd' | 'createdAt' | 'updatedAt'>) =>
    apiClient.put<WeeklyReviewResponse>(`/reviews/weeks/${weekStart}`, body),
};
```

- [ ] **Step 4: Export API**

Add to `src/services/api/index.ts`:

```ts
export * from './reviewApi';
```

- [ ] **Step 5: Run TypeScript build**

Run:

```bash
npm run build
```

Expected: PASS or fail only because UI components are not yet created. If it fails on `PageResponse` shape, inspect `src/services/api/types.ts` and reuse the existing generic page type name.

- [ ] **Step 6: Commit**

```bash
git add src/services/api/client.ts src/services/api/types.ts src/services/api/reviewApi.ts src/services/api/index.ts
git commit -m "Add review frontend API client"
```

---

### Task 5: Frontend Review Components

**Files:**
- Create: `src/components/reviews/MultiTagInput.tsx`
- Create: `src/components/reviews/StatsOverview.tsx`
- Create: `src/components/reviews/EntryForm.tsx`
- Create: `src/components/reviews/EntryList.tsx`
- Create: `src/components/reviews/WeeklyWorkbench.tsx`

- [ ] **Step 1: Create MultiTagInput**

Create `src/components/reviews/MultiTagInput.tsx`:

```tsx
import React, { useState } from 'react';
import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface MultiTagInputProps {
  value: string[];
  presets: string[];
  placeholder: string;
  onChange: (value: string[]) => void;
}

export const MultiTagInput = ({ value, presets, placeholder, onChange }: MultiTagInputProps) => {
  const [draft, setDraft] = useState('');
  const addTag = (tag: string) => {
    const normalized = tag.trim();
    if (!normalized || value.includes(normalized) || value.length >= 10) return;
    onChange([...value, normalized]);
    setDraft('');
  };
  const removeTag = (tag: string) => onChange(value.filter((item) => item !== tag));

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {value.map((tag) => (
          <Badge key={tag} variant="secondary" className="gap-1 bg-blue-50 text-blue-700 border border-blue-100">
            {tag}
            <button type="button" aria-label={`移除 ${tag}`} onClick={() => removeTag(tag)}>
              <X className="w-3 h-3" />
            </button>
          </Badge>
        ))}
      </div>
      <div className="flex gap-2">
        <Input value={draft} placeholder={placeholder} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.preventDefault();
            addTag(draft);
          }
        }} className="h-8 text-[11px]" />
        <Button type="button" variant="outline" size="sm" className="h-8 text-[10px]" onClick={() => addTag(draft)}>添加</Button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {presets.map((tag) => (
          <button key={tag} type="button" className="text-[10px] px-2 py-1 rounded border border-gray-200 text-gray-500 hover:bg-gray-50" onClick={() => addTag(tag)}>
            {tag}
          </button>
        ))}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Create StatsOverview**

Create `src/components/reviews/StatsOverview.tsx`:

```tsx
import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ReviewStatsResponse } from '@/services/api';

const topEntry = (items: Record<string, number>) => Object.entries(items).sort((a, b) => b[1] - a[1])[0];

export const StatsOverview = ({ stats }: { stats: ReviewStatsResponse | null }) => {
  const topProblem = stats ? topEntry(stats.problemTagCounts) : undefined;
  const topEmotion = stats ? topEntry(stats.emotionTagCounts) : undefined;
  const cards = [
    ['统计区间', stats ? `${stats.startDate} ~ ${stats.endDate}` : '-'],
    ['记录数', stats ? String(stats.totalCount) : '-'],
    ['交易 / 观察', stats ? `${stats.tradeActionCount} / ${stats.observationDecisionCount}` : '-'],
    ['计划外次数', stats ? String((stats.planStatusCounts.UNPLANNED || 0) + (stats.planStatusCounts.INTRADAY_ADJUSTMENT || 0)) : '-'],
    ['最高频问题', topProblem ? `${topProblem[0]} (${topProblem[1]})` : '-'],
    ['最高频情绪', topEmotion ? `${topEmotion[0]} (${topEmotion[1]})` : '-'],
    ['平均纪律', stats?.averageDisciplineScore == null ? '-' : stats.averageDisciplineScore.toFixed(2)],
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map(([label, value]) => (
        <Card key={label} className="rounded-lg border-gray-200 bg-white">
          <CardContent className="p-4">
            <p className="text-[10px] uppercase tracking-widest text-gray-400 font-bold">{label}</p>
            <p className="mt-2 text-lg font-bold text-gray-900">{value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};
```

- [ ] **Step 3: Create EntryForm**

Create `src/components/reviews/EntryForm.tsx` with controlled state for all `ReviewEntryRequest` fields. Include these exact placeholders:

```tsx
const PLACEHOLDERS = {
  reasonText: '例：看到神剑封板后，担心航天后排补涨，临盘追入航发中。',
  reflectionText: '这次主要是策略问题、判断问题、执行问题，还是情绪问题？',
  conclusionText: '例：计划外追后排，纪律评分偏低。',
  nextActionText: '写成一句未来可执行的话，例如：缩量反弹不加仓。',
  outcomeText: '例：次日低开，验证追高风险；或：暂未验证。',
};
```

Use `MultiTagInput` for `sectorTags`, `emotionTags`, and `problemTags`. Use native `select` styled with `h-8 rounded border border-gray-200 bg-white px-2 text-[11px]` for single-select fields.

- [ ] **Step 4: Create EntryList**

Create `src/components/reviews/EntryList.tsx` rendering `ReviewEntryResponse[]` in the existing table style. Show date, action, code/name, plan status, emotion tags, problem tags, discipline score, and `conclusionText`.

- [ ] **Step 5: Create WeeklyWorkbench**

Create `src/components/reviews/WeeklyWorkbench.tsx` with:

```tsx
interface WeeklyWorkbenchProps {
  data: WeeklyWorkbenchResponse | null;
  onSave: (payload: {
    summaryText: string;
    repeatedMistakesText: string;
    effectiveActionsText: string;
    emotionPatternText: string;
    nextWeekFocusText: string;
    ruleCandidatesText: string;
    linkedEntryIds: string[];
  }) => Promise<void>;
}
```

Render plan deviation entries, low discipline entries, and textareas with the prompt examples from the spec.

- [ ] **Step 6: Run build**

Run:

```bash
npm run build
```

Expected: PASS after imports and props are consistent.

- [ ] **Step 7: Commit**

```bash
git add src/components/reviews
git commit -m "Add review workbench components"
```

---

### Task 6: Reviews Page And Navigation

**Files:**
- Create: `src/pages/Reviews.tsx`
- Modify: `src/App.tsx`
- Modify: `src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Create page orchestration**

Create `src/pages/Reviews.tsx`:

```tsx
import React, { useEffect, useMemo, useState } from 'react';
import { BookOpenCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { EntryForm } from '@/components/reviews/EntryForm';
import { EntryList } from '@/components/reviews/EntryList';
import { StatsOverview } from '@/components/reviews/StatsOverview';
import { WeeklyWorkbench } from '@/components/reviews/WeeklyWorkbench';
import { reviewApi, ReviewEntryRequest, ReviewEntryResponse, ReviewStatsResponse, WeeklyWorkbenchResponse } from '@/services/api';

function isoToday() {
  return new Date().toISOString().slice(0, 10);
}

function mondayOf(dateText: string) {
  const date = new Date(`${dateText}T00:00:00`);
  const day = date.getDay() || 7;
  date.setDate(date.getDate() - day + 1);
  return date.toISOString().slice(0, 10);
}

function sundayOf(weekStart: string) {
  const date = new Date(`${weekStart}T00:00:00`);
  date.setDate(date.getDate() + 6);
  return date.toISOString().slice(0, 10);
}

export default function Reviews() {
  const [entries, setEntries] = useState<ReviewEntryResponse[]>([]);
  const [stats, setStats] = useState<ReviewStatsResponse | null>(null);
  const [workbench, setWorkbench] = useState<WeeklyWorkbenchResponse | null>(null);
  const [weekStart, setWeekStart] = useState(mondayOf(isoToday()));
  const weekEnd = useMemo(() => sundayOf(weekStart), [weekStart]);

  const load = async () => {
    const [entryPage, statsData, weekData] = await Promise.all([
      reviewApi.getEntries({ startDate: weekStart, endDate: weekEnd, pageSize: 50 }),
      reviewApi.getStats({ startDate: weekStart, endDate: weekEnd }),
      reviewApi.getWeek(weekStart),
    ]);
    setEntries(entryPage.items);
    setStats(statsData);
    setWorkbench(weekData);
  };

  useEffect(() => {
    load().catch((err: Error) => toast.error(err.message));
  }, [weekStart]);

  const createEntry = async (payload: ReviewEntryRequest) => {
    await reviewApi.createEntry(payload);
    toast.success('复盘记录已保存');
    await load();
  };

  const saveWeek = async (payload: Parameters<typeof reviewApi.saveWeek>[1]) => {
    await reviewApi.saveWeek(weekStart, payload);
    toast.success('周复盘已保存');
    await load();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2"><BookOpenCheck className="w-6 h-6" />交易复盘</h2>
          <p className="text-muted-foreground text-sm mt-1">把交易行为和观察决策沉淀成可统计、可周复盘的样本库。</p>
        </div>
        <input type="date" value={weekStart} onChange={(event) => setWeekStart(mondayOf(event.target.value))} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]" />
      </div>

      <StatsOverview stats={stats} />

      <Tabs defaultValue="entries">
        <TabsList>
          <TabsTrigger value="entries">复盘记录</TabsTrigger>
          <TabsTrigger value="weekly">周复盘工作台</TabsTrigger>
        </TabsList>
        <TabsContent value="entries" className="space-y-4">
          <Card className="rounded-lg border-gray-200 bg-white">
            <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">新增复盘记录</CardTitle></CardHeader>
            <CardContent><EntryForm onSubmit={createEntry} /></CardContent>
          </Card>
          <EntryList entries={entries} />
        </TabsContent>
        <TabsContent value="weekly">
          <WeeklyWorkbench data={workbench} onSave={saveWeek} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

- [ ] **Step 2: Register route**

Modify `src/App.tsx`:

```tsx
import Reviews from './pages/Reviews';
```

Add route inside `Layout`:

```tsx
<Route path="/reviews" element={<Reviews />} />
```

- [ ] **Step 3: Add sidebar item**

Modify `src/components/layout/Sidebar.tsx` imports:

```tsx
import { BookOpenCheck, Database, History, LayoutDashboard, MonitorPlay, Search, Settings, TrendingDown } from 'lucide-react';
```

Add nav item after `连板断板`:

```tsx
{ icon: BookOpenCheck, label: '交易复盘', path: '/reviews' },
```

- [ ] **Step 4: Run build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pages/Reviews.tsx src/App.tsx src/components/layout/Sidebar.tsx
git commit -m "Add trade review page"
```

---

### Task 7: End-To-End Verification

**Files:**
- Verify only unless defects are found.

- [ ] **Step 1: Run backend tests**

Run:

```bash
pytest tests/test_reviews.py tests/test_limit_up_break_monitor.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 3: Start dev stack**

Run:

```bash
./scripts/start-dev.sh
```

Expected: backend on `http://127.0.0.1:8000`, frontend on Vite port printed by the script.

- [ ] **Step 4: Manual browser verification**

Open the frontend URL and verify:

- Sidebar shows `交易复盘`.
- `/reviews` loads without console-visible crash.
- Creating a `交易行为` record succeeds.
- Creating an `观察决策` record succeeds.
- Overview metrics update.
- Weekly workbench shows plan deviation and low discipline records when applicable.
- Weekly summary saves and reloads.

- [ ] **Step 5: Final commit for fixes only**

If verification required fixes:

```bash
git add <changed-files>
git commit -m "Stabilize review workbench verification"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Manual record creation: Tasks 2, 3, 5, 6.
- Trade action and observation decision split: Tasks 2, 3, 5.
- SQLite storage and migration: Task 1.
- API endpoints: Task 3.
- Error stats and weekly workbench: Task 3 and Task 6.
- Placeholder guidance: Task 5.
- No AI, no trading integration, no new dependencies: preserved by all tasks.
- Frontend build and backend tests: Tasks 4, 5, 6, 7.

Placeholder scan:

- This plan intentionally contains no unresolved marker steps.
- Each code-changing task includes concrete file paths and code shapes.

Type consistency:

- Backend uses snake_case columns and camelCase API payloads.
- Frontend uses API camelCase types consistently.
- `conclusionText`, `weekStart`, `disciplineScore`, and tag array fields match the design spec.
