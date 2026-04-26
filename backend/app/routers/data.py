from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.data_service import DataFetchError, get_stock_data_status, list_fetch_logs, refresh_stock_data
from ..utils import api_error, ok

router = APIRouter()


@router.post("/data/stocks/{code}/refresh")
def refresh_stock(code: str, provider: str | None = Query(None), db: Session = Depends(get_db)):
    try:
        dataset = refresh_stock_data(db, code, provider)
        db.commit()
    except DataFetchError as exc:
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc
    return ok(
        {
            "code": dataset["stock"].code,
            "symbol": dataset["stock"].symbol,
            "provider": dataset["provider"],
            "priceBarCount": len(dataset["bars"]),
            "dataUpdatedAt": dataset["dataUpdatedAt"].isoformat() if dataset.get("dataUpdatedAt") else None,
            "dataCompleteness": dataset["dataCompleteness"],
            "usedCache": dataset["usedCache"],
            "dataStale": dataset["dataStale"],
            "refreshError": dataset["refreshError"],
        }
    )


@router.get("/data/stocks/{code}/status")
def stock_data_status(code: str, provider: str | None = Query(None), db: Session = Depends(get_db)):
    try:
        status = get_stock_data_status(db, code, provider)
    except DataFetchError as exc:
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc
    return ok(status)


@router.get("/data/fetch-logs")
def fetch_logs(
    code: str | None = None,
    provider: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ok(list_fetch_logs(db, code=code, provider=provider, page=page, page_size=pageSize))
