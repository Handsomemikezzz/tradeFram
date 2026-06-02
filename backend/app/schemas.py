from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TRADE_ACTIONS = {"BUY", "SELL", "ADD", "REDUCE", "CLEAR", "DO_T"}
OBSERVATION_ACTIONS = {"WANTED_BUY", "WANTED_SELL", "CANCELLED_ORDER", "HELD_BACK", "PLAN_OBSERVE"}
PLAN_STATUSES = {"PLANNED", "UNPLANNED", "INTRADAY_ADJUSTMENT", "OBSERVED_ONLY"}
CARD_STATUSES = {"OPEN", "CLOSED"}
CARD_INITIAL_ACTIONS = {"BUY", "WATCH", "PLAN_BUY"}
CARD_EVENT_TYPES = {"HOLD", "ADD", "REDUCE", "SELL", "DO_T", "PLAN_CHANGE", "EMOTION", "OBSERVATION"}
MAX_TAGS_PER_FIELD = 10


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _strip_required_text(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be blank")
    return stripped


class ApiError(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: ApiError | None = None
    requestId: str
    serverTime: str


class ResearchTaskCreate(BaseModel):
    code: str = Field(..., min_length=6, max_length=16)
    market: str = "A_SHARE"
    source: str = "USER_INPUT"
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def code_must_be_digits(cls, value: str) -> str:
        normalized = value.strip().upper()
        import re

        match = re.fullmatch(r"(?:(SH|SZ|BJ))?(\d{6})(?:\.(SH|SZ|BJ))?", normalized)
        if not match:
            raise ValueError("code must be a 6 digit A-share code, optionally with SH/SZ/BJ prefix or suffix")
        return match.group(2)


class WatchlistCreate(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)
    source: str = "USER"
    reportId: str | None = None
    note: str | None = None


class MonitoringCreate(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)
    strategyId: str | None = None
    strategyName: str | None = None
    enabled: bool = True
    source: str = "USER"
    reportId: str | None = None
    strategyParams: dict[str, Any] = Field(default_factory=dict)
    riskParams: dict[str, Any] = Field(default_factory=dict)


class MonitoringUpdate(BaseModel):
    enabled: bool | None = None
    reason: str | None = None


class EngineUpdate(BaseModel):
    active: bool
    reason: str | None = None


class PaperTradingRunScope(BaseModel):
    monitoringItemIds: list[str] = Field(default_factory=list)
    enabledOnly: bool = True


class PaperTradingRunCreate(BaseModel):
    trigger: Literal["MANUAL", "AUTO"] = "MANUAL"
    scope: PaperTradingRunScope = Field(default_factory=PaperTradingRunScope)
    dryRun: bool = False


class LimitUpBreakSnapshotCreate(BaseModel):
    tradeDate: date | None = None
    threshold: int = Field(default=2, ge=1)
    provider: str = "AkShare"


class ScreenerSnapshotCreate(BaseModel):
    tradeDate: date | None = None
    provider: str = "AkShare"
    strategyType: str = "pattern_a"


class Page(BaseModel):
    items: list[Any]
    page: int
    pageSize: int
    total: int
    hasMore: bool

    model_config = ConfigDict(populate_by_name=True)


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

    @model_validator(mode="after")
    def action_type_valid(self):
        allowed = TRADE_ACTIONS if self.entryType == "TRADE_ACTION" else OBSERVATION_ACTIONS
        if self.actionType not in allowed:
            raise ValueError("actionType is invalid for entryType")
        return self


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

    @field_validator("tradeDate")
    @classmethod
    def update_trade_date_not_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("tradeDate cannot be in the future")
        return value

    @field_validator("planStatus")
    @classmethod
    def update_plan_status_valid(cls, value: str | None) -> str | None:
        if value is not None and value not in PLAN_STATUSES:
            raise ValueError("planStatus is invalid")
        return value


class WeeklyReviewUpdate(BaseModel):
    summaryText: str = ""
    repeatedMistakesText: str = ""
    effectiveActionsText: str = ""
    emotionPatternText: str = ""
    nextWeekFocusText: str = ""
    ruleCandidatesText: str = ""
    linkedEntryIds: list[str] = Field(default_factory=list)


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
    initialImages: list[str] = Field(default_factory=list)
    
    # Professional Trading Audit Fields
    strategyType: str | None = None
    expectedRrRatio: str | None = None
    stopLossTarget: str | None = None

    @field_validator("code", "name", mode="before")
    @classmethod
    def strip_identity_text(cls, value: str | None) -> str | None:
        return _strip_optional_text(value)

    @field_validator("startDate")
    @classmethod
    def start_date_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("startDate cannot be in the future")
        return value

    @field_validator("initialReasonText")
    @classmethod
    def initial_reason_text_not_blank(cls, value: str) -> str:
        return _strip_required_text(value, "initialReasonText")

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
    initialImages: list[str] | None = Field(default=None)
    
    # Professional Trading Audit Fields
    strategyType: str | None = None
    expectedRrRatio: str | None = None
    stopLossTarget: str | None = None
    pnlAmount: float | None = None
    rMultiple: float | None = None
    marketRegime: str | None = None
    exitQuality: str | None = None

    @field_validator("code", "name", mode="before")
    @classmethod
    def strip_update_identity_text(cls, value: str | None) -> str | None:
        return _strip_optional_text(value)

    @field_validator("initialReasonText")
    @classmethod
    def update_initial_reason_text_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_required_text(value, "initialReasonText")

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
    images: list[str] = Field(default_factory=list)

    @field_validator("title", "reasonText")
    @classmethod
    def event_required_text_not_blank(cls, value: str) -> str:
        return _strip_required_text(value, "event text")

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
    images: list[str] | None = Field(default=None)

    @field_validator("title", "reasonText")
    @classmethod
    def update_event_required_text_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_required_text(value, "event text")

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
    closeImages: list[str] = Field(default_factory=list)
    
    # Professional Trading Audit Fields
    pnlAmount: float | None = None
    rMultiple: float | None = None
    marketRegime: str | None = None
    exitQuality: str | None = None

    @field_validator(
        "sellReasonText",
        "pnlText",
        "didWellText",
        "didWrongText",
        "reflectionText",
        "ruleText",
    )
    @classmethod
    def close_required_text_not_blank(cls, value: str) -> str:
        return _strip_required_text(value, "close text")

    @field_validator("endDate")
    @classmethod
    def end_date_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("endDate cannot be in the future")
        return value


class IronLawCreate(BaseModel):
    text: str = Field(..., min_length=1)
    tag: str = Field(..., min_length=1)
    status: Literal["COMPLIANT", "CHALLENGED", "VIOLATED"] = "COMPLIANT"


class IronLawUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1)
    tag: str | None = Field(default=None, min_length=1)
    status: Literal["COMPLIANT", "CHALLENGED", "VIOLATED"] | None = None


class HotStockSnapshotCreate(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    forceRefresh: bool = True
    source: str = "EastmoneyHotRank"
