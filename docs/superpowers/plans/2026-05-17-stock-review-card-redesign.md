# Stock Review Card Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current `/reviews` page's primary workflow with stock-centered review cards while preserving the old entry and weekly review APIs.

**Architecture:** Add `StockReviewCard` as the review unit and `StockReviewEvent` as its optional timeline. Keep all review routes in the existing `backend/app/routers/reviews.py`, keep serializers in `backend/app/serializers_reviews.py`, and switch `src/pages/Reviews.tsx` to a two-column card/detail UI. The legacy `ReviewEntry` and `WeeklyReview` code stays available for compatibility but stops being the primary frontend workflow.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic v2, React 19, TypeScript, Vite, existing shadcn-style UI components.

---

## Review Decisions Folded Into This Plan

- Use `GET /api/v1/reviews/cards/summary`, not `/cards/stats`, to avoid FastAPI path conflicts with `/cards/{cardId}`.
- `StockReviewCard.code` is optional. When no concrete stock code exists, `name` and `sectorTags` carry free-text context.
- Reuse the existing `backend/app/routers/reviews.py` router. Do not register a second reviews router in `backend/app/main.py`.
- `close` requires `endDate`, `sellReasonText`, `pnlText`, `followedPlan`, `disciplineScore`, `didWellText`, `didWrongText`, `reflectionText`, and `ruleText`; repeated close on an already closed card returns `400 REVIEW_CARD_ALREADY_CLOSED`.
- `reopen` preserves all close fields, changes only `status` to `OPEN`, clears no data, and allows new events. Closing again overwrites close fields.
- Add `sectorTags` to the card and `positionSnapshot` to events as text-first fields.
- `initialAction` is an independent enum with labels: `BUY=买入建仓`, `WATCH=开始关注`, `PLAN_BUY=计划买入`.
- Use a two-column Reviews UI: left card list, right card detail.
- Keep `pnlText` as free text for this implementation; do not add numeric PnL aggregation.
- `close` and `reopen` return the full card detail response including events.

## File Structure

- Modify `backend/app/models.py`: add `StockReviewCard` and `StockReviewEvent` SQLAlchemy models.
- Modify `backend/app/schemas.py`: add request schemas and validators for cards, events, close, reopen, and list filters.
- Modify `backend/app/services/reviews.py`: add card/event CRUD, summary, close/reopen state transitions, and validation.
- Modify `backend/app/routers/reviews.py`: add card routes before `/reviews/cards/{card_id}` detail route; keep existing entry/week routes.
- Modify `backend/app/serializers_reviews.py`: add `stock_review_card_payload` and `stock_review_event_payload`.
- Create `alembic/versions/20260517_0003_stock_review_cards.py`: add `stock_review_cards` and `stock_review_events`.
- Modify `tests/test_reviews.py`: extend existing review tests with card/event API coverage.
- Modify `src/services/api/types.ts`: add frontend card/event request and response types.
- Create `src/services/api/reviewCardApi.ts`: card API client.
- Modify `src/services/api/index.ts`: export the new API module.
- Create `src/components/reviews/CardForm.tsx`: initial card creation form.
- Create `src/components/reviews/CardList.tsx`: filterable stock review card list.
- Create `src/components/reviews/CardDetail.tsx`: two-column detail panel host.
- Create `src/components/reviews/EventForm.tsx`: process event form.
- Create `src/components/reviews/EventTimeline.tsx`: ordered timeline display.
- Modify `src/components/reviews/reviewLabels.ts`: add labels for card status, initial action, event type, followed-plan values.
- Rewrite `src/pages/Reviews.tsx`: switch primary workflow to cards while keeping `/reviews` route and title.

---

### Task 1: Backend Models And Migration

**Files:**
- Modify: `backend/app/models.py`
- Create: `alembic/versions/20260517_0003_stock_review_cards.py`
- Test: `tests/test_reviews.py`

- [ ] **Step 1: Add model persistence test**

Add this test after `test_review_models_can_persist_json_tags` in `tests/test_reviews.py`:

```python
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
```

- [ ] **Step 2: Run model test and verify it fails**

Run:

```bash
pytest tests/test_reviews.py::test_stock_review_card_models_can_persist_events -v
```

Expected: FAIL with `AttributeError: module 'backend.app.models' has no attribute 'StockReviewCard'`.

- [ ] **Step 3: Add SQLAlchemy models**

Add these classes in `backend/app/models.py` immediately after `WeeklyReview`:

```python
class StockReviewCard(Base):
    __tablename__ = "stock_review_cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN", index=True)
    code: Mapped[str | None] = mapped_column(String(6), index=True)
    name: Mapped[str | None] = mapped_column(String(64))
    sector_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)
    initial_action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    initial_position_context: Mapped[str | None] = mapped_column(String(32))
    initial_plan_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    initial_reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_move_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    original_plan_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    initial_emotion_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    problem_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sell_reason_text: Mapped[str | None] = mapped_column(Text)
    pnl_text: Mapped[str | None] = mapped_column(Text)
    followed_plan: Mapped[bool | None] = mapped_column(Boolean)
    discipline_score: Mapped[int | None] = mapped_column(Integer)
    did_well_text: Mapped[str | None] = mapped_column(Text)
    did_wrong_text: Mapped[str | None] = mapped_column(Text)
    reflection_text: Mapped[str | None] = mapped_column(Text)
    rule_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    events: Mapped[list["StockReviewEvent"]] = relationship(
        "StockReviewEvent",
        back_populates="card",
        cascade="all, delete-orphan",
        order_by="StockReviewEvent.event_date.asc(), StockReviewEvent.created_at.asc()",
    )


class StockReviewEvent(Base):
    __tablename__ = "stock_review_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("stock_review_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(96), nullable=False)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    position_snapshot: Mapped[str | None] = mapped_column(String(128))
    deviated_from_plan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    emotion_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    problem_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)

    card: Mapped[StockReviewCard] = relationship("StockReviewCard", back_populates="events")
```

Ensure `Boolean` and `ForeignKey` are imported from SQLAlchemy near the top of `backend/app/models.py`:

```python
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
```

- [ ] **Step 4: Add Alembic migration**

Create `alembic/versions/20260517_0003_stock_review_cards.py`:

```python
"""stock review cards

Revision ID: 20260517_0003
Revises: 20260517_0002
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_0003"
down_revision = "20260517_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_review_cards",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=True),
        sa.Column("sector_tags", sa.JSON(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("initial_action", sa.String(length=32), nullable=False),
        sa.Column("initial_position_context", sa.String(length=32), nullable=True),
        sa.Column("initial_plan_status", sa.String(length=32), nullable=False),
        sa.Column("initial_reason_text", sa.Text(), nullable=False),
        sa.Column("expected_move_text", sa.Text(), nullable=False),
        sa.Column("original_plan_text", sa.Text(), nullable=False),
        sa.Column("initial_emotion_tags", sa.JSON(), nullable=False),
        sa.Column("problem_tags", sa.JSON(), nullable=False),
        sa.Column("sell_reason_text", sa.Text(), nullable=True),
        sa.Column("pnl_text", sa.Text(), nullable=True),
        sa.Column("followed_plan", sa.Boolean(), nullable=True),
        sa.Column("discipline_score", sa.Integer(), nullable=True),
        sa.Column("did_well_text", sa.Text(), nullable=True),
        sa.Column("did_wrong_text", sa.Text(), nullable=True),
        sa.Column("reflection_text", sa.Text(), nullable=True),
        sa.Column("rule_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_review_cards_status", "stock_review_cards", ["status"])
    op.create_index("ix_stock_review_cards_code", "stock_review_cards", ["code"])
    op.create_index("ix_stock_review_cards_start_date", "stock_review_cards", ["start_date"])
    op.create_index("ix_stock_review_cards_end_date", "stock_review_cards", ["end_date"])
    op.create_index("ix_stock_review_cards_initial_action", "stock_review_cards", ["initial_action"])
    op.create_index("ix_stock_review_cards_initial_plan_status", "stock_review_cards", ["initial_plan_status"])

    op.create_table(
        "stock_review_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("card_id", sa.String(length=64), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=96), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("position_snapshot", sa.String(length=128), nullable=True),
        sa.Column("deviated_from_plan", sa.Boolean(), nullable=False),
        sa.Column("emotion_tags", sa.JSON(), nullable=False),
        sa.Column("problem_tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["stock_review_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_review_events_card_id", "stock_review_events", ["card_id"])
    op.create_index("ix_stock_review_events_event_date", "stock_review_events", ["event_date"])
    op.create_index("ix_stock_review_events_event_type", "stock_review_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_stock_review_events_event_type", table_name="stock_review_events")
    op.drop_index("ix_stock_review_events_event_date", table_name="stock_review_events")
    op.drop_index("ix_stock_review_events_card_id", table_name="stock_review_events")
    op.drop_table("stock_review_events")
    op.drop_index("ix_stock_review_cards_initial_plan_status", table_name="stock_review_cards")
    op.drop_index("ix_stock_review_cards_initial_action", table_name="stock_review_cards")
    op.drop_index("ix_stock_review_cards_end_date", table_name="stock_review_cards")
    op.drop_index("ix_stock_review_cards_start_date", table_name="stock_review_cards")
    op.drop_index("ix_stock_review_cards_code", table_name="stock_review_cards")
    op.drop_index("ix_stock_review_cards_status", table_name="stock_review_cards")
    op.drop_table("stock_review_cards")
```

- [ ] **Step 5: Run model test and verify it passes**

Run:

```bash
pytest tests/test_reviews.py::test_stock_review_card_models_can_persist_events -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py alembic/versions/20260517_0003_stock_review_cards.py tests/test_reviews.py
git commit -m "Add stock review card storage" -m "Constraint: Preserve existing review_entry and weekly_review tables.
Confidence: high
Scope-risk: narrow
Tested: pytest tests/test_reviews.py::test_stock_review_card_models_can_persist_events -v"
```

---

### Task 2: Backend Schemas And Serializers

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/serializers_reviews.py`
- Test: `tests/test_reviews.py`

- [ ] **Step 1: Add schema validation tests**

Add these tests near the other review validation tests in `tests/test_reviews.py`:

```python
def test_stock_review_card_create_requires_name_when_code_missing():
    reset_database()
    client = TestClient(app)

    response = client.post(
        "/api/v1/reviews/cards",
        json={
            "startDate": "2026-05-11",
            "initialAction": "WATCH",
            "initialPlanStatus": "OBSERVED_ONLY",
            "initialReasonText": "观察板块机会",
            "expectedMoveText": "",
            "originalPlanText": "",
            "sectorTags": ["商业航天"],
            "initialEmotionTags": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_stock_review_card_close_requires_discipline_score():
    reset_database()
    client = TestClient(app)
    card = create_card(client)

    response = client.post(
        f"/api/v1/reviews/cards/{card['id']}/close",
        json={
            "endDate": "2026-05-13",
            "sellReasonText": "跌破计划线",
            "pnlText": "小亏",
            "followedPlan": True,
            "didWellText": "按计划离场",
            "didWrongText": "买点偏急",
            "reflectionText": "下次等确认",
            "ruleText": "跌破计划线直接走",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
```

Add this helper before the new tests:

```python
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
```

- [ ] **Step 2: Run schema tests and verify they fail**

Run:

```bash
pytest tests/test_reviews.py::test_stock_review_card_create_requires_name_when_code_missing tests/test_reviews.py::test_stock_review_card_close_requires_discipline_score -v
```

Expected: FAIL because `/api/v1/reviews/cards` does not exist yet.

- [ ] **Step 3: Add constants and schemas**

Add these constants near the existing review constants in `backend/app/schemas.py`:

```python
CARD_STATUSES = {"OPEN", "CLOSED"}
CARD_INITIAL_ACTIONS = {"BUY", "WATCH", "PLAN_BUY"}
CARD_EVENT_TYPES = {"HOLD", "ADD", "REDUCE", "SELL", "PLAN_CHANGE", "EMOTION", "OBSERVATION"}
```

Add these schemas after `WeeklyReviewUpdate`:

```python
class StockReviewCardCreate(BaseModel):
    code: str | None = Field(default=None, min_length=6, max_length=6)
    name: str | None = Field(default=None, max_length=64)
    sectorTags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_FIELD)
    startDate: date
    initialAction: str
    initialPositionContext: str | None = None
    initialPlanStatus: str
    initialReasonText: str = Field(..., min_length=1)
    expectedMoveText: str = ""
    originalPlanText: str = ""
    initialEmotionTags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_FIELD)

    @field_validator("startDate")
    @classmethod
    def start_date_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("startDate cannot be in the future")
        return value

    @field_validator("initialAction")
    @classmethod
    def initial_action_valid(cls, value: str) -> str:
        if value not in CARD_INITIAL_ACTIONS:
            raise ValueError("initialAction is invalid")
        return value

    @field_validator("initialPlanStatus")
    @classmethod
    def initial_plan_status_valid(cls, value: str) -> str:
        if value not in PLAN_STATUSES:
            raise ValueError("initialPlanStatus is invalid")
        return value

    @model_validator(mode="after")
    def code_or_name_required(self):
        if not self.code and not self.name:
            raise ValueError("code or name is required")
        return self


class StockReviewCardUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=6, max_length=6)
    name: str | None = Field(default=None, max_length=64)
    sectorTags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_FIELD)
    startDate: date | None = None
    initialAction: str | None = None
    initialPositionContext: str | None = None
    initialPlanStatus: str | None = None
    initialReasonText: str | None = Field(default=None, min_length=1)
    expectedMoveText: str | None = None
    originalPlanText: str | None = None
    initialEmotionTags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_FIELD)

    @field_validator("startDate")
    @classmethod
    def update_start_date_not_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("startDate cannot be in the future")
        return value

    @field_validator("initialAction")
    @classmethod
    def update_initial_action_valid(cls, value: str | None) -> str | None:
        if value is not None and value not in CARD_INITIAL_ACTIONS:
            raise ValueError("initialAction is invalid")
        return value

    @field_validator("initialPlanStatus")
    @classmethod
    def update_initial_plan_status_valid(cls, value: str | None) -> str | None:
        if value is not None and value not in PLAN_STATUSES:
            raise ValueError("initialPlanStatus is invalid")
        return value


class StockReviewEventCreate(BaseModel):
    eventDate: date
    eventType: str
    title: str = Field(..., min_length=1, max_length=96)
    reasonText: str = Field(..., min_length=1)
    positionSnapshot: str | None = Field(default=None, max_length=128)
    deviatedFromPlan: bool = False
    emotionTags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_FIELD)
    problemTags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_FIELD)

    @field_validator("eventDate")
    @classmethod
    def event_date_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("eventDate cannot be in the future")
        return value

    @field_validator("eventType")
    @classmethod
    def event_type_valid(cls, value: str) -> str:
        if value not in CARD_EVENT_TYPES:
            raise ValueError("eventType is invalid")
        return value


class StockReviewEventUpdate(BaseModel):
    eventDate: date | None = None
    eventType: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=96)
    reasonText: str | None = Field(default=None, min_length=1)
    positionSnapshot: str | None = Field(default=None, max_length=128)
    deviatedFromPlan: bool | None = None
    emotionTags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_FIELD)
    problemTags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_FIELD)

    @field_validator("eventDate")
    @classmethod
    def update_event_date_not_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("eventDate cannot be in the future")
        return value

    @field_validator("eventType")
    @classmethod
    def update_event_type_valid(cls, value: str | None) -> str | None:
        if value is not None and value not in CARD_EVENT_TYPES:
            raise ValueError("eventType is invalid")
        return value


class StockReviewCardClose(BaseModel):
    endDate: date
    sellReasonText: str = Field(..., min_length=1)
    pnlText: str = Field(..., min_length=1)
    followedPlan: bool
    disciplineScore: int = Field(..., ge=1, le=5)
    problemTags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_FIELD)
    didWellText: str = Field(..., min_length=1)
    didWrongText: str = Field(..., min_length=1)
    reflectionText: str = Field(..., min_length=1)
    ruleText: str = Field(..., min_length=1)

    @field_validator("endDate")
    @classmethod
    def end_date_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("endDate cannot be in the future")
        return value
```

- [ ] **Step 4: Add serializers**

Add these functions to `backend/app/serializers_reviews.py`:

```python
def stock_review_event_payload(event: m.StockReviewEvent) -> dict:
    return {
        "id": event.id,
        "cardId": event.card_id,
        "eventDate": event.event_date.isoformat(),
        "eventType": event.event_type,
        "title": event.title,
        "reasonText": event.reason_text,
        "positionSnapshot": event.position_snapshot,
        "deviatedFromPlan": event.deviated_from_plan,
        "emotionTags": event.emotion_tags or [],
        "problemTags": event.problem_tags or [],
        "createdAt": event.created_at.isoformat(),
        "updatedAt": event.updated_at.isoformat(),
    }


def stock_review_card_payload(card: m.StockReviewCard, *, include_events: bool = False) -> dict:
    payload = {
        "id": card.id,
        "status": card.status,
        "code": card.code,
        "name": card.name,
        "sectorTags": card.sector_tags or [],
        "startDate": card.start_date.isoformat(),
        "endDate": card.end_date.isoformat() if card.end_date else None,
        "initialAction": card.initial_action,
        "initialPositionContext": card.initial_position_context,
        "initialPlanStatus": card.initial_plan_status,
        "initialReasonText": card.initial_reason_text,
        "expectedMoveText": card.expected_move_text,
        "originalPlanText": card.original_plan_text,
        "initialEmotionTags": card.initial_emotion_tags or [],
        "problemTags": card.problem_tags or [],
        "sellReasonText": card.sell_reason_text,
        "pnlText": card.pnl_text,
        "followedPlan": card.followed_plan,
        "disciplineScore": card.discipline_score,
        "didWellText": card.did_well_text,
        "didWrongText": card.did_wrong_text,
        "reflectionText": card.reflection_text,
        "ruleText": card.rule_text,
        "createdAt": card.created_at.isoformat(),
        "updatedAt": card.updated_at.isoformat(),
    }
    if include_events:
        payload["events"] = [stock_review_event_payload(event) for event in card.events]
    return payload
```

- [ ] **Step 5: Run schema tests**

Run:

```bash
pytest tests/test_reviews.py::test_stock_review_card_create_requires_name_when_code_missing tests/test_reviews.py::test_stock_review_card_close_requires_discipline_score -v
```

Expected after routes are still missing: FAIL with 404. This confirms schema code imports cleanly and the remaining failure is route implementation.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/serializers_reviews.py tests/test_reviews.py
git commit -m "Define stock review card schemas" -m "Constraint: Card code remains optional to support watch-only and board-level review cards.
Confidence: high
Scope-risk: narrow
Tested: pytest tests/test_reviews.py::test_stock_review_card_create_requires_name_when_code_missing tests/test_reviews.py::test_stock_review_card_close_requires_discipline_score -v"
```

---

### Task 3: Backend Card Services And Routes

**Files:**
- Modify: `backend/app/services/reviews.py`
- Modify: `backend/app/routers/reviews.py`
- Test: `tests/test_reviews.py`

- [ ] **Step 1: Add API behavior tests**

Add this test block to `tests/test_reviews.py`:

```python
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

    summary = assert_ok(client.get("/api/v1/reviews/cards/summary", params={"startDate": "2026-05-11", "endDate": "2026-05-17"}))
    assert summary["openCount"] == 0
    assert summary["closedCount"] == 1
    assert summary["createdInRangeCount"] == 1
    assert summary["closedInRangeCount"] == 1
    assert summary["lowDisciplineClosedCount"] == 0

    reopened = assert_ok(client.post(f"/api/v1/reviews/cards/{card['id']}/reopen"))
    assert reopened["status"] == "OPEN"
    assert reopened["sellReasonText"] == "跌破计划线"
```

- [ ] **Step 2: Run API test and verify it fails**

Run:

```bash
pytest tests/test_reviews.py::test_stock_review_card_lifecycle_and_summary -v
```

Expected: FAIL with 404 for `/api/v1/reviews/cards`.

- [ ] **Step 3: Add service imports**

Modify imports in `backend/app/services/reviews.py`:

```python
from sqlalchemy import desc, or_
```

Extend schema imports:

```python
from ..schemas import (
    ReviewEntryCreate,
    ReviewEntryUpdate,
    StockReviewCardClose,
    StockReviewCardCreate,
    StockReviewCardUpdate,
    StockReviewEventCreate,
    StockReviewEventUpdate,
    WeeklyReviewUpdate,
)
```

- [ ] **Step 4: Add service functions**

Append these functions to `backend/app/services/reviews.py`:

```python
def create_stock_review_card(db: Session, payload: StockReviewCardCreate) -> m.StockReviewCard:
    card = m.StockReviewCard(
        id=new_id("src"),
        status="OPEN",
        code=payload.code,
        name=payload.name,
        sector_tags=payload.sectorTags,
        start_date=payload.startDate,
        initial_action=payload.initialAction,
        initial_position_context=payload.initialPositionContext,
        initial_plan_status=payload.initialPlanStatus,
        initial_reason_text=payload.initialReasonText,
        expected_move_text=payload.expectedMoveText,
        original_plan_text=payload.originalPlanText,
        initial_emotion_tags=payload.initialEmotionTags,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def get_stock_review_card_or_404(db: Session, card_id: str) -> m.StockReviewCard:
    card = db.get(m.StockReviewCard, card_id)
    if card is None:
        raise api_error(404, "REVIEW_CARD_NOT_FOUND", f"标的复盘卡片 {card_id} 不存在")
    return card


def list_stock_review_cards(
    db: Session,
    *,
    status: str | None = None,
    keyword: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    plan_status: str | None = None,
    problem_tags: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[m.StockReviewCard], int]:
    query = db.query(m.StockReviewCard)
    if status and status != "ALL":
        query = query.filter(m.StockReviewCard.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(m.StockReviewCard.code.like(like), m.StockReviewCard.name.like(like)))
    if start_date:
        query = query.filter(m.StockReviewCard.start_date >= start_date)
    if end_date:
        query = query.filter(m.StockReviewCard.start_date <= end_date)
    if plan_status:
        query = query.filter(m.StockReviewCard.initial_plan_status == plan_status)

    all_items = query.order_by(desc(m.StockReviewCard.start_date), desc(m.StockReviewCard.created_at)).all()
    filtered = [item for item in all_items if _contains_all(item.problem_tags or [], problem_tags)]
    total = len(filtered)
    start = (page - 1) * page_size
    return filtered[start : start + page_size], total


def update_stock_review_card(db: Session, card_id: str, payload: StockReviewCardUpdate) -> m.StockReviewCard:
    card = get_stock_review_card_or_404(db, card_id)
    data = payload.model_dump(exclude_unset=True)
    field_map = {
        "sectorTags": "sector_tags",
        "startDate": "start_date",
        "initialAction": "initial_action",
        "initialPositionContext": "initial_position_context",
        "initialPlanStatus": "initial_plan_status",
        "initialReasonText": "initial_reason_text",
        "expectedMoveText": "expected_move_text",
        "originalPlanText": "original_plan_text",
        "initialEmotionTags": "initial_emotion_tags",
    }
    for key, value in data.items():
        setattr(card, field_map.get(key, key), value)
    card.updated_at = m.now_utc()
    db.commit()
    db.refresh(card)
    return card


def create_stock_review_event(db: Session, card_id: str, payload: StockReviewEventCreate) -> m.StockReviewEvent:
    get_stock_review_card_or_404(db, card_id)
    event = m.StockReviewEvent(
        id=new_id("sre"),
        card_id=card_id,
        event_date=payload.eventDate,
        event_type=payload.eventType,
        title=payload.title,
        reason_text=payload.reasonText,
        position_snapshot=payload.positionSnapshot,
        deviated_from_plan=payload.deviatedFromPlan,
        emotion_tags=payload.emotionTags,
        problem_tags=payload.problemTags,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_stock_review_event_or_404(db: Session, card_id: str, event_id: str) -> m.StockReviewEvent:
    event = db.get(m.StockReviewEvent, event_id)
    if event is None or event.card_id != card_id:
        raise api_error(404, "REVIEW_EVENT_NOT_FOUND", f"过程记录 {event_id} 不存在")
    return event


def update_stock_review_event(db: Session, card_id: str, event_id: str, payload: StockReviewEventUpdate) -> m.StockReviewEvent:
    event = get_stock_review_event_or_404(db, card_id, event_id)
    data = payload.model_dump(exclude_unset=True)
    field_map = {
        "eventDate": "event_date",
        "eventType": "event_type",
        "reasonText": "reason_text",
        "positionSnapshot": "position_snapshot",
        "deviatedFromPlan": "deviated_from_plan",
        "emotionTags": "emotion_tags",
        "problemTags": "problem_tags",
    }
    for key, value in data.items():
        setattr(event, field_map.get(key, key), value)
    event.updated_at = m.now_utc()
    db.commit()
    db.refresh(event)
    return event


def delete_stock_review_event(db: Session, card_id: str, event_id: str) -> None:
    event = get_stock_review_event_or_404(db, card_id, event_id)
    db.delete(event)
    db.commit()


def close_stock_review_card(db: Session, card_id: str, payload: StockReviewCardClose) -> m.StockReviewCard:
    card = get_stock_review_card_or_404(db, card_id)
    if card.status == "CLOSED":
        raise api_error(400, "REVIEW_CARD_ALREADY_CLOSED", "标的复盘卡片已经结束")
    if payload.endDate < card.start_date:
        raise api_error(422, "INVALID_REVIEW_END_DATE", "endDate 不能早于 startDate")
    card.status = "CLOSED"
    card.end_date = payload.endDate
    card.sell_reason_text = payload.sellReasonText
    card.pnl_text = payload.pnlText
    card.followed_plan = payload.followedPlan
    card.discipline_score = payload.disciplineScore
    card.problem_tags = payload.problemTags
    card.did_well_text = payload.didWellText
    card.did_wrong_text = payload.didWrongText
    card.reflection_text = payload.reflectionText
    card.rule_text = payload.ruleText
    card.updated_at = m.now_utc()
    db.commit()
    db.refresh(card)
    return card


def reopen_stock_review_card(db: Session, card_id: str) -> m.StockReviewCard:
    card = get_stock_review_card_or_404(db, card_id)
    card.status = "OPEN"
    card.updated_at = m.now_utc()
    db.commit()
    db.refresh(card)
    return card


def get_stock_review_card_summary(db: Session, *, start_date: date, end_date: date) -> dict:
    cards = db.query(m.StockReviewCard).all()
    closed_in_range = [card for card in cards if card.end_date and start_date <= card.end_date <= end_date]
    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "openCount": sum(1 for card in cards if card.status == "OPEN"),
        "closedCount": sum(1 for card in cards if card.status == "CLOSED"),
        "createdInRangeCount": sum(1 for card in cards if start_date <= card.start_date <= end_date),
        "closedInRangeCount": len(closed_in_range),
        "lowDisciplineClosedCount": sum(1 for card in closed_in_range if card.discipline_score is not None and card.discipline_score <= LOW_DISCIPLINE_SCORE_THRESHOLD),
        "lowDisciplineThreshold": LOW_DISCIPLINE_SCORE_THRESHOLD,
    }
```

- [ ] **Step 5: Add routes**

Modify imports in `backend/app/routers/reviews.py` to include the new schemas and serializers:

```python
from ..schemas import (
    ReviewEntryCreate,
    ReviewEntryUpdate,
    StockReviewCardClose,
    StockReviewCardCreate,
    StockReviewCardUpdate,
    StockReviewEventCreate,
    StockReviewEventUpdate,
    WeeklyReviewUpdate,
)
from ..serializers_reviews import review_entry_payload, stock_review_card_payload, stock_review_event_payload, weekly_review_payload
```

Extend service imports with:

```python
    close_stock_review_card,
    create_stock_review_card,
    create_stock_review_event,
    delete_stock_review_event,
    get_stock_review_card_or_404,
    get_stock_review_card_summary,
    list_stock_review_cards,
    reopen_stock_review_card,
    update_stock_review_card,
    update_stock_review_event,
```

Add these routes after `router = APIRouter()` and before `/reviews/entries` routes:

```python
@router.post("/reviews/cards")
def post_stock_review_card(payload: StockReviewCardCreate, db: Session = Depends(get_db)):
    return ok(stock_review_card_payload(create_stock_review_card(db, payload), include_events=True))


@router.get("/reviews/cards")
def get_stock_review_cards(
    status: str | None = None,
    keyword: str | None = None,
    startDate: date | None = None,
    endDate: date | None = None,
    planStatus: str | None = None,
    problemTags: list[str] | None = Query(default=None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = list_stock_review_cards(
        db,
        status=status,
        keyword=keyword,
        start_date=startDate,
        end_date=endDate,
        plan_status=planStatus,
        problem_tags=problemTags,
        page=page,
        page_size=pageSize,
    )
    return ok({"items": [stock_review_card_payload(item) for item in items], "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})


@router.get("/reviews/cards/summary")
def get_stock_review_cards_summary(startDate: date, endDate: date, db: Session = Depends(get_db)):
    return ok(get_stock_review_card_summary(db, start_date=startDate, end_date=endDate))


@router.get("/reviews/cards/{card_id}")
def get_stock_review_card(card_id: str, db: Session = Depends(get_db)):
    return ok(stock_review_card_payload(get_stock_review_card_or_404(db, card_id), include_events=True))


@router.patch("/reviews/cards/{card_id}")
def patch_stock_review_card(card_id: str, payload: StockReviewCardUpdate, db: Session = Depends(get_db)):
    return ok(stock_review_card_payload(update_stock_review_card(db, card_id, payload), include_events=True))


@router.post("/reviews/cards/{card_id}/events")
def post_stock_review_event(card_id: str, payload: StockReviewEventCreate, db: Session = Depends(get_db)):
    return ok(stock_review_event_payload(create_stock_review_event(db, card_id, payload)))


@router.patch("/reviews/cards/{card_id}/events/{event_id}")
def patch_stock_review_event(card_id: str, event_id: str, payload: StockReviewEventUpdate, db: Session = Depends(get_db)):
    return ok(stock_review_event_payload(update_stock_review_event(db, card_id, event_id, payload)))


@router.delete("/reviews/cards/{card_id}/events/{event_id}")
def remove_stock_review_event(card_id: str, event_id: str, db: Session = Depends(get_db)):
    delete_stock_review_event(db, card_id, event_id)
    return ok({"deleted": True})


@router.post("/reviews/cards/{card_id}/close")
def close_review_card(card_id: str, payload: StockReviewCardClose, db: Session = Depends(get_db)):
    return ok(stock_review_card_payload(close_stock_review_card(db, card_id, payload), include_events=True))


@router.post("/reviews/cards/{card_id}/reopen")
def reopen_review_card(card_id: str, db: Session = Depends(get_db)):
    return ok(stock_review_card_payload(reopen_stock_review_card(db, card_id), include_events=True))
```

- [ ] **Step 6: Run backend review tests**

Run:

```bash
pytest tests/test_reviews.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/reviews.py backend/app/routers/reviews.py tests/test_reviews.py
git commit -m "Add stock review card API" -m "Constraint: Card summary uses /reviews/cards/summary to avoid path conflicts with card detail.
Rejected: Register a second reviews router | existing review routes already share one router surface.
Confidence: high
Scope-risk: moderate
Tested: pytest tests/test_reviews.py -v"
```

---

### Task 4: Frontend API Types And Labels

**Files:**
- Modify: `src/services/api/types.ts`
- Create: `src/services/api/reviewCardApi.ts`
- Modify: `src/services/api/index.ts`
- Modify: `src/components/reviews/reviewLabels.ts`
- Verification: `npm run lint`

- [ ] **Step 1: Add TypeScript API types**

Append these types after the existing review types in `src/services/api/types.ts`:

```ts
export type StockReviewCardStatus = 'OPEN' | 'CLOSED';
export type StockReviewInitialAction = 'BUY' | 'WATCH' | 'PLAN_BUY';
export type StockReviewEventType = 'HOLD' | 'ADD' | 'REDUCE' | 'SELL' | 'PLAN_CHANGE' | 'EMOTION' | 'OBSERVATION';

export interface StockReviewEventResponse {
  id: string;
  cardId: string;
  eventDate: string;
  eventType: StockReviewEventType;
  title: string;
  reasonText: string;
  positionSnapshot: string | null;
  deviatedFromPlan: boolean;
  emotionTags: string[];
  problemTags: string[];
  createdAt: string;
  updatedAt: string;
}

export interface StockReviewCardResponse {
  id: string;
  status: StockReviewCardStatus;
  code: string | null;
  name: string | null;
  sectorTags: string[];
  startDate: string;
  endDate: string | null;
  initialAction: StockReviewInitialAction;
  initialPositionContext: string | null;
  initialPlanStatus: ReviewPlanStatus;
  initialReasonText: string;
  expectedMoveText: string;
  originalPlanText: string;
  initialEmotionTags: string[];
  problemTags: string[];
  sellReasonText: string | null;
  pnlText: string | null;
  followedPlan: boolean | null;
  disciplineScore: number | null;
  didWellText: string | null;
  didWrongText: string | null;
  reflectionText: string | null;
  ruleText: string | null;
  createdAt: string;
  updatedAt: string;
  events?: StockReviewEventResponse[];
}

export interface StockReviewCardRequest {
  code?: string | null;
  name?: string | null;
  sectorTags: string[];
  startDate: string;
  initialAction: StockReviewInitialAction;
  initialPositionContext?: string | null;
  initialPlanStatus: ReviewPlanStatus;
  initialReasonText: string;
  expectedMoveText: string;
  originalPlanText: string;
  initialEmotionTags: string[];
}

export interface StockReviewEventRequest {
  eventDate: string;
  eventType: StockReviewEventType;
  title: string;
  reasonText: string;
  positionSnapshot?: string | null;
  deviatedFromPlan: boolean;
  emotionTags: string[];
  problemTags: string[];
}

export interface StockReviewCardCloseRequest {
  endDate: string;
  sellReasonText: string;
  pnlText: string;
  followedPlan: boolean;
  disciplineScore: number;
  problemTags: string[];
  didWellText: string;
  didWrongText: string;
  reflectionText: string;
  ruleText: string;
}

export interface StockReviewCardSummaryResponse {
  startDate: string;
  endDate: string;
  openCount: number;
  closedCount: number;
  createdInRangeCount: number;
  closedInRangeCount: number;
  lowDisciplineClosedCount: number;
  lowDisciplineThreshold: number;
}
```

- [ ] **Step 2: Add card API client**

Create `src/services/api/reviewCardApi.ts`:

```ts
import { apiClient, QueryParams } from './client';
import {
  PageResponse,
  StockReviewCardCloseRequest,
  StockReviewCardRequest,
  StockReviewCardResponse,
  StockReviewCardSummaryResponse,
  StockReviewEventRequest,
  StockReviewEventResponse,
} from './types';

export const reviewCardApi = {
  createCard: (body: StockReviewCardRequest) => apiClient.post<StockReviewCardResponse>('/reviews/cards', body),
  getCards: (query?: QueryParams) => apiClient.get<PageResponse<StockReviewCardResponse>>('/reviews/cards', query),
  getSummary: (query: { startDate: string; endDate: string }) => apiClient.get<StockReviewCardSummaryResponse>('/reviews/cards/summary', query),
  getCard: (id: string) => apiClient.get<StockReviewCardResponse>(`/reviews/cards/${id}`),
  updateCard: (id: string, body: Partial<StockReviewCardRequest>) => apiClient.patch<StockReviewCardResponse>(`/reviews/cards/${id}`, body),
  addEvent: (id: string, body: StockReviewEventRequest) => apiClient.post<StockReviewEventResponse>(`/reviews/cards/${id}/events`, body),
  updateEvent: (cardId: string, eventId: string, body: Partial<StockReviewEventRequest>) => apiClient.patch<StockReviewEventResponse>(`/reviews/cards/${cardId}/events/${eventId}`, body),
  deleteEvent: (cardId: string, eventId: string) => apiClient.delete<{ deleted: boolean }>(`/reviews/cards/${cardId}/events/${eventId}`),
  closeCard: (id: string, body: StockReviewCardCloseRequest) => apiClient.post<StockReviewCardResponse>(`/reviews/cards/${id}/close`, body),
  reopenCard: (id: string) => apiClient.post<StockReviewCardResponse>(`/reviews/cards/${id}/reopen`, {}),
};
```

- [ ] **Step 3: Export API client**

Add this line to `src/services/api/index.ts`:

```ts
export * from './reviewCardApi';
```

- [ ] **Step 4: Add labels**

Append these maps to `src/components/reviews/reviewLabels.ts`:

```ts
export const stockReviewStatusLabel: Record<string, string> = {
  OPEN: '进行中',
  CLOSED: '已结束',
};

export const stockReviewInitialActionLabel: Record<string, string> = {
  BUY: '买入建仓',
  WATCH: '开始关注',
  PLAN_BUY: '计划买入',
};

export const stockReviewEventTypeLabel: Record<string, string> = {
  HOLD: '继续持有',
  ADD: '加仓',
  REDUCE: '减仓',
  SELL: '卖出',
  PLAN_CHANGE: '计划变化',
  EMOTION: '情绪波动',
  OBSERVATION: '观察记录',
};

export const followedPlanLabel: Record<string, string> = {
  true: '按计划执行',
  false: '偏离计划',
};
```

- [ ] **Step 5: Run TypeScript check**

Run:

```bash
npm run lint
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/services/api/types.ts src/services/api/reviewCardApi.ts src/services/api/index.ts src/components/reviews/reviewLabels.ts
git commit -m "Add stock review card frontend API types" -m "Constraint: initialAction is an independent card enum with explicit labels.
Confidence: high
Scope-risk: narrow
Tested: npm run lint"
```

---

### Task 5: Frontend Card Creation And List

**Files:**
- Create: `src/components/reviews/CardForm.tsx`
- Create: `src/components/reviews/CardList.tsx`
- Modify: `src/pages/Reviews.tsx`
- Verification: `npm run lint`

- [ ] **Step 1: Create card form component**

Create `src/components/reviews/CardForm.tsx`:

```tsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ReviewPlanStatus, StockReviewCardRequest, StockReviewInitialAction } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { emotionPresets, sectorPresets } from './reviewLabels';

const today = () => new Date().toISOString().slice(0, 10);
const selectClass = 'h-8 rounded border border-gray-200 bg-white px-2 text-[11px]';
const textareaClass = 'min-h-20 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

interface CardFormProps {
  onSubmit: (payload: StockReviewCardRequest) => Promise<void>;
}

export const CardForm = ({ onSubmit }: CardFormProps) => {
  const [submitting, setSubmitting] = useState(false);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [sectorTags, setSectorTags] = useState<string[]>([]);
  const [startDate, setStartDate] = useState(today());
  const [initialAction, setInitialAction] = useState<StockReviewInitialAction>('BUY');
  const [initialPositionContext, setInitialPositionContext] = useState('LIGHT');
  const [initialPlanStatus, setInitialPlanStatus] = useState<ReviewPlanStatus>('PLANNED');
  const [initialReasonText, setInitialReasonText] = useState('');
  const [expectedMoveText, setExpectedMoveText] = useState('');
  const [originalPlanText, setOriginalPlanText] = useState('');
  const [initialEmotionTags, setInitialEmotionTags] = useState<string[]>([]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        code: code.trim() || null,
        name: name.trim() || null,
        sectorTags,
        startDate,
        initialAction,
        initialPositionContext,
        initialPlanStatus,
        initialReasonText,
        expectedMoveText,
        originalPlanText,
        initialEmotionTags,
      });
      setCode('');
      setName('');
      setSectorTags([]);
      setInitialReasonText('');
      setExpectedMoveText('');
      setOriginalPlanText('');
      setInitialEmotionTags([]);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-5" onSubmit={submit}>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">股票代码</span>
          <Input value={code} maxLength={6} placeholder="可为空，例如 600519" onChange={(event) => setCode(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">股票名称/主题</span>
          <Input value={name} placeholder="例如 航天电子，或 商业航天观察" onChange={(event) => setName(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">开始日期</span>
          <Input type="date" value={startDate} max={today()} onChange={(event) => setStartDate(event.target.value)} className="h-8 text-[11px]" />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">初始动作</span>
          <select className={selectClass} value={initialAction} onChange={(event) => setInitialAction(event.target.value as StockReviewInitialAction)}>
            <option value="BUY">买入建仓</option>
            <option value="WATCH">开始关注</option>
            <option value="PLAN_BUY">计划买入</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">初始仓位</span>
          <select className={selectClass} value={initialPositionContext} onChange={(event) => setInitialPositionContext(event.target.value)}>
            <option value="EMPTY">空仓</option>
            <option value="LIGHT">轻仓</option>
            <option value="HALF">半仓</option>
            <option value="HEAVY">重仓</option>
            <option value="FULL">满仓</option>
            <option value="HOLDING">持有中</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">计划状态</span>
          <select className={selectClass} value={initialPlanStatus} onChange={(event) => setInitialPlanStatus(event.target.value as ReviewPlanStatus)}>
            <option value="PLANNED">计划内</option>
            <option value="UNPLANNED">计划外</option>
            <option value="INTRADAY_ADJUSTMENT">临盘调整</option>
            <option value="OBSERVED_ONLY">观察未执行</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">板块/题材</span>
          <MultiTagInput value={sectorTags} presets={sectorPresets} placeholder="输入板块，例如 商业航天" onChange={setSectorTags} />
        </div>
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase text-gray-500">建卡情绪</span>
          <MultiTagInput value={initialEmotionTags} presets={emotionPresets} placeholder="输入情绪，例如 冷静" onChange={setInitialEmotionTags} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">买入/关注理由</span>
          <textarea className={textareaClass} value={initialReasonText} placeholder="例：计划内低吸，题材强度仍在。" onChange={(event) => setInitialReasonText(event.target.value)} required />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">预期逻辑</span>
          <textarea className={textareaClass} value={expectedMoveText} placeholder="例：预期放量突破后继续走强。" onChange={(event) => setExpectedMoveText(event.target.value)} />
        </label>
        <label className="space-y-1 flex flex-col">
          <span className="text-[10px] font-bold uppercase text-gray-500">原计划</span>
          <textarea className={textareaClass} value={originalPlanText} placeholder="例：跌破五日线离场；冲高不封板减仓。" onChange={(event) => setOriginalPlanText(event.target.value)} />
        </label>
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={submitting} className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700">
          {submitting ? '保存中...' : '新建标的复盘'}
        </Button>
      </div>
    </form>
  );
};
```

- [ ] **Step 2: Create card list component**

Create `src/components/reviews/CardList.tsx`:

```tsx
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { StockReviewCardResponse } from '@/services/api';
import { reviewPlanStatusLabel, stockReviewInitialActionLabel, stockReviewStatusLabel } from './reviewLabels';

interface CardListProps {
  cards: StockReviewCardResponse[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function durationDays(card: StockReviewCardResponse) {
  const end = card.endDate || new Date().toISOString().slice(0, 10);
  const startTime = new Date(`${card.startDate}T00:00:00`).getTime();
  const endTime = new Date(`${end}T00:00:00`).getTime();
  return Math.max(1, Math.floor((endTime - startTime) / 86400000) + 1);
}

export const CardList = ({ cards, selectedId, onSelect }: CardListProps) => (
  <div className="space-y-2">
    {cards.length === 0 && (
      <Card className="rounded-lg border-gray-200 bg-white">
        <CardContent className="p-6 text-center text-[12px] text-gray-400">暂无标的复盘卡片。</CardContent>
      </Card>
    )}
    {cards.map((card) => {
      const latestEvent = card.events?.[card.events.length - 1];
      return (
        <button key={card.id} type="button" onClick={() => onSelect(card.id)} className="block w-full text-left">
          <Card className={selectedId === card.id ? 'rounded-lg border-blue-300 bg-blue-50' : 'rounded-lg border-gray-200 bg-white hover:bg-gray-50'}>
            <CardContent className="p-3 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-mono text-[12px] font-bold text-gray-900">{card.code || '-'}</div>
                  <div className="text-[12px] text-gray-600">{card.name || card.sectorTags.join(' / ') || '-'}</div>
                </div>
                <Badge variant="secondary" className="text-[9px]">{stockReviewStatusLabel[card.status] || card.status}</Badge>
              </div>
              <div className="flex flex-wrap gap-1">
                <Badge variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{stockReviewInitialActionLabel[card.initialAction]}</Badge>
                <Badge variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{reviewPlanStatusLabel[card.initialPlanStatus]}</Badge>
                <Badge variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{durationDays(card)} 天</Badge>
              </div>
              <p className="line-clamp-2 text-[11px] text-gray-600">{card.initialReasonText}</p>
              {latestEvent && <p className="text-[10px] text-gray-400">最近：{latestEvent.eventDate} / {latestEvent.title}</p>}
              {card.status === 'CLOSED' && (
                <div className="flex items-center justify-between text-[10px] text-gray-500">
                  <span>{card.pnlText || '未填盈亏'}</span>
                  <span>纪律 {card.disciplineScore ?? '-'}</span>
                </div>
              )}
            </CardContent>
          </Card>
        </button>
      );
    })}
  </div>
);
```

- [ ] **Step 3: Wire basic card list into Reviews page**

Replace `src/pages/Reviews.tsx` with a temporary card-list-only version:

```tsx
import React, { useEffect, useMemo, useState } from 'react';
import { BookOpenCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CardForm } from '@/components/reviews/CardForm';
import { CardList } from '@/components/reviews/CardList';
import { reviewCardApi, StockReviewCardRequest, StockReviewCardResponse, StockReviewCardSummaryResponse } from '@/services/api';

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
  const [cards, setCards] = useState<StockReviewCardResponse[]>([]);
  const [summary, setSummary] = useState<StockReviewCardSummaryResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [status, setStatus] = useState<'OPEN' | 'CLOSED' | 'ALL'>('OPEN');
  const [keyword, setKeyword] = useState('');
  const [weekStart, setWeekStart] = useState(mondayOf(isoToday()));
  const weekEnd = useMemo(() => sundayOf(weekStart), [weekStart]);

  const load = async () => {
    const [page, summaryData] = await Promise.all([
      reviewCardApi.getCards({ status, keyword: keyword || undefined, pageSize: 50 }),
      reviewCardApi.getSummary({ startDate: weekStart, endDate: weekEnd }),
    ]);
    setCards(page.items);
    setSummary(summaryData);
    if (!selectedId && page.items[0]) setSelectedId(page.items[0].id);
  };

  useEffect(() => {
    load().catch((err: Error) => toast.error(err.message));
  }, [status, weekStart]);

  const createCard = async (payload: StockReviewCardRequest) => {
    const created = await reviewCardApi.createCard(payload);
    toast.success('标的复盘卡片已建立');
    setSelectedId(created.id);
    await load();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BookOpenCheck className="w-6 h-6" />
            交易复盘
          </h2>
          <p className="text-muted-foreground text-sm mt-1">为每只股票建立一张复盘卡片，记录买入逻辑、持有过程、卖出结果和纪律反思。</p>
        </div>
        <label className="space-y-1">
          <span className="block text-[10px] uppercase tracking-widest text-gray-400 font-bold">统计周起始</span>
          <input type="date" value={weekStart} onChange={(event) => setWeekStart(mondayOf(event.target.value))} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]" />
        </label>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="进行中" value={summary?.openCount ?? 0} />
        <Metric label="本周新建" value={summary?.createdInRangeCount ?? 0} />
        <Metric label="本周结束" value={summary?.closedInRangeCount ?? 0} />
        <Metric label="低纪律结束" value={summary?.lowDisciplineClosedCount ?? 0} />
      </div>

      <Card className="rounded-lg border-gray-200 bg-white">
        <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">新建标的复盘</CardTitle></CardHeader>
        <CardContent><CardForm onSubmit={createCard} /></CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-2">
        <select value={status} onChange={(event) => setStatus(event.target.value as 'OPEN' | 'CLOSED' | 'ALL')} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]">
          <option value="OPEN">进行中</option>
          <option value="CLOSED">已结束</option>
          <option value="ALL">全部</option>
        </select>
        <input value={keyword} onChange={(event) => setKeyword(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') load().catch((err: Error) => toast.error(err.message)); }} placeholder="搜索代码或名称" className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]" />
      </div>

      <CardList cards={cards} selectedId={selectedId} onSelect={setSelectedId} />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <Card className="rounded-lg border-gray-200 bg-white">
      <CardContent className="p-4">
        <div className="text-[10px] font-bold uppercase text-gray-400">{label}</div>
        <div className="mt-1 font-mono text-2xl font-bold text-gray-900">{value}</div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run TypeScript check**

Run:

```bash
npm run lint
```

Expected: PASS. If it fails because `Button` is unused in `CardList.tsx`, remove the `Button` import and hidden element.

- [ ] **Step 5: Commit**

```bash
git add src/components/reviews/CardForm.tsx src/components/reviews/CardList.tsx src/pages/Reviews.tsx
git commit -m "Switch reviews page to stock review cards" -m "Constraint: Keep existing /reviews route and sidebar entry.
Confidence: medium
Scope-risk: moderate
Tested: npm run lint"
```

---

### Task 6: Frontend Detail, Timeline, Close, And Reopen

**Files:**
- Create: `src/components/reviews/EventForm.tsx`
- Create: `src/components/reviews/EventTimeline.tsx`
- Create: `src/components/reviews/CardDetail.tsx`
- Modify: `src/pages/Reviews.tsx`
- Verification: `npm run lint`

- [ ] **Step 1: Create event form**

Create `src/components/reviews/EventForm.tsx`:

```tsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StockReviewEventRequest, StockReviewEventType } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { emotionPresets, problemPresets } from './reviewLabels';

const today = () => new Date().toISOString().slice(0, 10);
const selectClass = 'h-8 rounded border border-gray-200 bg-white px-2 text-[11px]';
const textareaClass = 'min-h-20 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

export const EventForm = ({ onSubmit }: { onSubmit: (payload: StockReviewEventRequest) => Promise<void> }) => {
  const [submitting, setSubmitting] = useState(false);
  const [eventDate, setEventDate] = useState(today());
  const [eventType, setEventType] = useState<StockReviewEventType>('HOLD');
  const [title, setTitle] = useState('');
  const [reasonText, setReasonText] = useState('');
  const [positionSnapshot, setPositionSnapshot] = useState('');
  const [deviatedFromPlan, setDeviatedFromPlan] = useState(false);
  const [emotionTags, setEmotionTags] = useState<string[]>([]);
  const [problemTags, setProblemTags] = useState<string[]>([]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        eventDate,
        eventType,
        title,
        reasonText,
        positionSnapshot: positionSnapshot.trim() || null,
        deviatedFromPlan,
        emotionTags,
        problemTags,
      });
      setTitle('');
      setReasonText('');
      setPositionSnapshot('');
      setDeviatedFromPlan(false);
      setEmotionTags([]);
      setProblemTags([]);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-3" onSubmit={submit}>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <Input type="date" value={eventDate} max={today()} onChange={(event) => setEventDate(event.target.value)} className="h-8 text-[11px]" />
        <select className={selectClass} value={eventType} onChange={(event) => setEventType(event.target.value as StockReviewEventType)}>
          <option value="HOLD">继续持有</option>
          <option value="ADD">加仓</option>
          <option value="REDUCE">减仓</option>
          <option value="SELL">卖出</option>
          <option value="PLAN_CHANGE">计划变化</option>
          <option value="EMOTION">情绪波动</option>
          <option value="OBSERVATION">观察记录</option>
        </select>
        <Input value={title} placeholder="事件标题" onChange={(event) => setTitle(event.target.value)} className="h-8 text-[11px]" required />
        <Input value={positionSnapshot} placeholder="仓位变化，例如 减至半仓" onChange={(event) => setPositionSnapshot(event.target.value)} className="h-8 text-[11px]" />
      </div>
      <textarea className={textareaClass} value={reasonText} placeholder="记录当时决策理由或观察" onChange={(event) => setReasonText(event.target.value)} required />
      <label className="flex items-center gap-2 text-[11px] text-gray-600">
        <input type="checkbox" checked={deviatedFromPlan} onChange={(event) => setDeviatedFromPlan(event.target.checked)} />
        偏离原计划
      </label>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <MultiTagInput value={emotionTags} presets={emotionPresets} placeholder="情绪标签" onChange={setEmotionTags} />
        <MultiTagInput value={problemTags} presets={problemPresets} placeholder="问题归因" onChange={setProblemTags} />
      </div>
      <div className="flex justify-end">
        <Button type="submit" disabled={submitting} className="h-8 text-[10px] font-bold uppercase tracking-widest">
          {submitting ? '保存中...' : '追加记录'}
        </Button>
      </div>
    </form>
  );
};
```

- [ ] **Step 2: Create event timeline**

Create `src/components/reviews/EventTimeline.tsx`:

```tsx
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { StockReviewEventResponse } from '@/services/api';
import { stockReviewEventTypeLabel } from './reviewLabels';

export const EventTimeline = ({ events }: { events: StockReviewEventResponse[] }) => {
  if (events.length === 0) {
    return <div className="rounded border border-dashed border-gray-200 p-4 text-center text-[12px] text-gray-400">暂无过程记录。</div>;
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div key={event.id} className="rounded-lg border border-gray-200 bg-white p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-[11px] font-mono text-gray-400">{event.eventDate}</div>
              <div className="text-[13px] font-bold text-gray-900">{event.title}</div>
            </div>
            <Badge variant="secondary" className="text-[9px]">{stockReviewEventTypeLabel[event.eventType] || event.eventType}</Badge>
          </div>
          <p className="mt-2 whitespace-pre-wrap text-[12px] text-gray-700">{event.reasonText}</p>
          <div className="mt-2 flex flex-wrap gap-1">
            {event.positionSnapshot && <Badge variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{event.positionSnapshot}</Badge>}
            {event.deviatedFromPlan && <Badge variant="secondary" className="text-[9px] bg-red-50 text-red-700">偏离计划</Badge>}
            {[...event.emotionTags, ...event.problemTags].map((tag) => (
              <Badge key={`${event.id}-${tag}`} variant="secondary" className="text-[9px] bg-gray-100 text-gray-600">{tag}</Badge>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
```

- [ ] **Step 3: Create card detail component**

Create `src/components/reviews/CardDetail.tsx`:

```tsx
import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StockReviewCardCloseRequest, StockReviewCardResponse, StockReviewEventRequest } from '@/services/api';
import { MultiTagInput } from './MultiTagInput';
import { EventForm } from './EventForm';
import { EventTimeline } from './EventTimeline';
import { problemPresets, reviewPlanStatusLabel, stockReviewInitialActionLabel, stockReviewStatusLabel } from './reviewLabels';

const today = () => new Date().toISOString().slice(0, 10);
const textareaClass = 'min-h-20 rounded border border-gray-200 bg-white px-3 py-2 text-[11px] outline-none focus:ring-2 focus:ring-blue-100';

interface CardDetailProps {
  card: StockReviewCardResponse | null;
  onAddEvent: (payload: StockReviewEventRequest) => Promise<void>;
  onClose: (payload: StockReviewCardCloseRequest) => Promise<void>;
  onReopen: () => Promise<void>;
}

export const CardDetail = ({ card, onAddEvent, onClose, onReopen }: CardDetailProps) => {
  const [endDate, setEndDate] = useState(today());
  const [sellReasonText, setSellReasonText] = useState('');
  const [pnlText, setPnlText] = useState('');
  const [followedPlan, setFollowedPlan] = useState(true);
  const [disciplineScore, setDisciplineScore] = useState(3);
  const [problemTags, setProblemTags] = useState<string[]>([]);
  const [didWellText, setDidWellText] = useState('');
  const [didWrongText, setDidWrongText] = useState('');
  const [reflectionText, setReflectionText] = useState('');
  const [ruleText, setRuleText] = useState('');

  if (!card) {
    return <Card className="rounded-lg border-gray-200 bg-white"><CardContent className="p-8 text-center text-gray-400">选择一张复盘卡片查看详情。</CardContent></Card>;
  }

  const submitClose = async (event: React.FormEvent) => {
    event.preventDefault();
    await onClose({ endDate, sellReasonText, pnlText, followedPlan, disciplineScore, problemTags, didWellText, didWrongText, reflectionText, ruleText });
  };

  return (
    <div className="space-y-4">
      <Card className="rounded-lg border-gray-200 bg-white">
        <CardHeader className="flex flex-row items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{card.code || '-'} {card.name || card.sectorTags.join(' / ')}</CardTitle>
            <p className="mt-1 text-[11px] text-gray-500">{stockReviewStatusLabel[card.status]} / {stockReviewInitialActionLabel[card.initialAction]} / {reviewPlanStatusLabel[card.initialPlanStatus]}</p>
          </div>
          {card.status === 'CLOSED' && (
            <Button type="button" variant="outline" className="h-8 text-[10px]" onClick={onReopen}>
              <RotateCcw className="mr-1 h-3 w-3" />
              重新打开
            </Button>
          )}
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px]">
          <InfoBlock label="买入/关注理由" value={card.initialReasonText} />
          <InfoBlock label="预期逻辑" value={card.expectedMoveText || '-'} />
          <InfoBlock label="原计划" value={card.originalPlanText || '-'} />
        </CardContent>
      </Card>

      <Card className="rounded-lg border-gray-200 bg-white">
        <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">过程时间线</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <EventTimeline events={card.events || []} />
          {card.status === 'OPEN' && <EventForm onSubmit={onAddEvent} />}
        </CardContent>
      </Card>

      <Card className="rounded-lg border-gray-200 bg-white">
        <CardHeader><CardTitle className="text-[10px] uppercase tracking-widest">结束复盘</CardTitle></CardHeader>
        <CardContent>
          {card.status === 'CLOSED' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px]">
              <InfoBlock label="卖出逻辑" value={card.sellReasonText || '-'} />
              <InfoBlock label="最终盈亏" value={card.pnlText || '-'} />
              <InfoBlock label="做对了什么" value={card.didWellText || '-'} />
              <InfoBlock label="做错了什么" value={card.didWrongText || '-'} />
              <InfoBlock label="后续反思" value={card.reflectionText || '-'} />
              <InfoBlock label="下次规则" value={card.ruleText || '-'} />
            </div>
          ) : (
            <form className="space-y-3" onSubmit={submitClose}>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <input type="date" value={endDate} max={today()} onChange={(event) => setEndDate(event.target.value)} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]" />
                <input value={pnlText} placeholder="最终盈亏，例如 亏损 2%" onChange={(event) => setPnlText(event.target.value)} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]" required />
                <select value={String(followedPlan)} onChange={(event) => setFollowedPlan(event.target.value === 'true')} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]">
                  <option value="true">按计划执行</option>
                  <option value="false">偏离计划</option>
                </select>
                <select value={disciplineScore} onChange={(event) => setDisciplineScore(Number(event.target.value))} className="h-8 rounded border border-gray-200 bg-white px-2 text-[11px]">
                  {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>纪律 {score}</option>)}
                </select>
              </div>
              <MultiTagInput value={problemTags} presets={problemPresets} placeholder="结束归因，例如 执行问题" onChange={setProblemTags} />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <textarea className={textareaClass} value={sellReasonText} placeholder="卖出或结束逻辑" onChange={(event) => setSellReasonText(event.target.value)} required />
                <textarea className={textareaClass} value={didWellText} placeholder="做对了什么" onChange={(event) => setDidWellText(event.target.value)} required />
                <textarea className={textareaClass} value={didWrongText} placeholder="做错了什么" onChange={(event) => setDidWrongText(event.target.value)} required />
                <textarea className={textareaClass} value={reflectionText} placeholder="后续反思" onChange={(event) => setReflectionText(event.target.value)} required />
                <textarea className={`${textareaClass} md:col-span-2`} value={ruleText} placeholder="下次可执行规则" onChange={(event) => setRuleText(event.target.value)} required />
              </div>
              <div className="flex justify-end">
                <Button type="submit" className="h-8 text-[10px] font-bold uppercase tracking-widest bg-blue-600 hover:bg-blue-700">结束复盘</Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-gray-100 bg-gray-50 p-3">
      <div className="text-[10px] font-bold uppercase text-gray-400">{label}</div>
      <div className="mt-1 whitespace-pre-wrap text-gray-700">{value}</div>
    </div>
  );
}
```

- [ ] **Step 4: Wire two-column detail into Reviews page**

Modify `src/pages/Reviews.tsx`:

Add imports:

```tsx
import { CardDetail } from '@/components/reviews/CardDetail';
import { StockReviewCardCloseRequest, StockReviewEventRequest } from '@/services/api';
```

Add state:

```tsx
const [selectedCard, setSelectedCard] = useState<StockReviewCardResponse | null>(null);
```

Replace `setSelectedId(page.items[0].id)` in `load` with:

```tsx
const nextSelectedId = selectedId || page.items[0]?.id || null;
if (nextSelectedId) {
  setSelectedId(nextSelectedId);
  setSelectedCard(await reviewCardApi.getCard(nextSelectedId));
} else {
  setSelectedCard(null);
}
```

Add handlers:

```tsx
const selectCard = async (id: string) => {
  setSelectedId(id);
  setSelectedCard(await reviewCardApi.getCard(id));
};

const addEvent = async (payload: StockReviewEventRequest) => {
  if (!selectedId) return;
  await reviewCardApi.addEvent(selectedId, payload);
  toast.success('过程记录已追加');
  await selectCard(selectedId);
  await load();
};

const closeCard = async (payload: StockReviewCardCloseRequest) => {
  if (!selectedId) return;
  const closed = await reviewCardApi.closeCard(selectedId, payload);
  toast.success('复盘已结束');
  setSelectedCard(closed);
  await load();
};

const reopenCard = async () => {
  if (!selectedId) return;
  const reopened = await reviewCardApi.reopenCard(selectedId);
  toast.success('复盘已重新打开');
  setSelectedCard(reopened);
  await load();
};
```

Replace the final `<CardList ... />` with:

```tsx
<div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
  <div className="lg:col-span-1">
    <CardList cards={cards} selectedId={selectedId} onSelect={(id) => selectCard(id).catch((err: Error) => toast.error(err.message))} />
  </div>
  <div className="lg:col-span-3">
    <CardDetail card={selectedCard} onAddEvent={addEvent} onClose={closeCard} onReopen={reopenCard} />
  </div>
</div>
```

- [ ] **Step 5: Run TypeScript check**

Run:

```bash
npm run lint
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/components/reviews/EventForm.tsx src/components/reviews/EventTimeline.tsx src/components/reviews/CardDetail.tsx src/pages/Reviews.tsx
git commit -m "Add stock review card detail workflow" -m "Constraint: Use a two-column detail UI inside the existing reviews page.
Confidence: medium
Scope-risk: moderate
Tested: npm run lint"
```

---

### Task 7: Full Verification And Cleanup

**Files:**
- Read/verify: all changed files
- Test: backend and frontend checks

- [ ] **Step 1: Run backend review tests**

Run:

```bash
pytest tests/test_reviews.py -v
```

Expected: PASS.

- [ ] **Step 2: Run broader backend regression checks**

Run:

```bash
pytest tests/test_cors.py tests/test_report_quote_consistency.py tests/test_reviews.py -v
```

Expected: PASS.

- [ ] **Step 3: Run frontend typecheck**

Run:

```bash
npm run lint
```

Expected: PASS.

- [ ] **Step 4: Run production build**

Run:

```bash
npm run build
```

Expected: PASS and Vite emits `dist/`.

- [ ] **Step 5: Manual browser verification**

Start the dev stack:

```bash
npm run start:dev
```

Open `http://localhost:3000/reviews` and verify:

- The existing sidebar entry still opens `交易复盘`.
- The new page shows `新建标的复盘`.
- Creating a card with `600519 / 贵州茅台` succeeds.
- Selecting the card shows the right-side detail panel.
- Adding a `继续持有` event updates the timeline.
- Ending the card changes status to `已结束`.
- Reopening the card changes status back to `进行中` and preserves close fields.

- [ ] **Step 6: Final git status**

Run:

```bash
git status --short
```

Expected: only intentional files changed, no generated noise except accepted `dist/` absence.

- [ ] **Step 7: Commit verification fixes**

If Step 1-6 required fixes, commit them:

```bash
git add backend/app src tests alembic docs/superpowers/plans/2026-05-17-stock-review-card-redesign.md
git commit -m "Verify stock review card workflow" -m "Constraint: Complete workflow must pass backend tests, TypeScript check, and Vite build.
Confidence: high
Scope-risk: narrow
Tested: pytest tests/test_reviews.py -v; pytest tests/test_cors.py tests/test_report_quote_consistency.py tests/test_reviews.py -v; npm run lint; npm run build"
```

If no fixes were needed, skip this commit.

## Self-Review

- Spec coverage: card model, event model, optional code, sector tags, position snapshot, close/reopen semantics, summary endpoint, two-column UI, old API preservation, and current `/reviews` route are all covered by tasks.
- Review coverage: H1-H4 are addressed in Task 2 and Task 3; M1-M5 are addressed across Task 1-6; L1-L4 are addressed except full timeline edit/delete UI, which has backend and API support but is not exposed in the first UI because creation and viewing satisfy the first workflow.
- Type consistency: backend snake_case fields map to camelCase serializers and TypeScript request/response types consistently.
- Remaining risk: Task 5 and Task 6 include sizeable TSX changes. Keep each task separate and run `npm run lint` before moving on.
