from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .routers import audit, data, data_health, limit_up_breaks, monitoring, p0b, portfolio, research, reviews, system, trading
from .seed import init_db
from .utils import http_exception_handler, validation_exception_handler


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="A股研投模拟系统 Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.get("/health")
def health():
    return {"ok": True}


for router in [system.router, data.router, data_health.router, research.router, reviews.router, monitoring.router, limit_up_breaks.router, trading.router, portfolio.router, audit.router, p0b.router]:
    app.include_router(router, prefix="/api/v1")
