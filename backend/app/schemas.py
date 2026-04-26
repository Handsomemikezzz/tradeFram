from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class Page(BaseModel):
    items: list[Any]
    page: int
    pageSize: int
    total: int
    hasMore: bool

    model_config = ConfigDict(populate_by_name=True)
