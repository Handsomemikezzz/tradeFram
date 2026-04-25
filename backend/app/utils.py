from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

CN_TZ = ZoneInfo("Asia/Shanghai")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone(CN_TZ).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{stamp}_{uuid4().hex[:8]}"


def dt_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(CN_TZ).isoformat(timespec="seconds")


def ok(data: Any = None) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "requestId": new_id("req"),
        "serverTime": now_iso(),
    }


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details},
        "requestId": new_id("req"),
        "serverTime": now_iso(),
    }


def api_error(status_code: int, code: str, message: str, details: Any = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "details": details})


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        detail = exc.detail
        payload = error_payload(
            str(detail.get("code", "HTTP_ERROR")),
            str(detail.get("message", exc.status_code)),
            detail.get("details"),
        )
    else:
        payload = error_payload("HTTP_ERROR", str(exc.detail), None)
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload("VALIDATION_ERROR", "请求参数校验失败", exc.errors()),
    )
