from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TRADE_ACTIONS = {"BUY", "SELL", "ADD", "REDUCE", "CLEAR", "DO_T"}
OBSERVATION_ACTIONS = {"WANTED_BUY", "WANTED_SELL", "CANCELLED_ORDER", "HELD_BACK", "PLAN_OBSERVE"}
PLAN_STATUSES = {"PLANNED", "UNPLANNED", "INTRADAY_ADJUSTMENT", "OBSERVED_ONLY"}
MAX_TAGS_PER_FIELD = 10


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
