from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..utils import dt_iso, ok, now_iso

router = APIRouter()


@router.get("/system/status")
def system_status(db: Session = Depends(get_db)):
    engine = db.get(m.PaperTradingEngineState, "default")
    return ok(
        {
            "status": "NORMAL",
            "mode": "PAPER_TRADING_ONLY",
            "tradeDay": True,
            "market": "SH_SZ",
            "currentTime": now_iso(),
            "paperTrading": {
                "active": bool(engine.active) if engine else False,
                "pollingEnabled": bool(engine.polling_enabled) if engine else False,
                "lastRunId": engine.last_run_id if engine else None,
            },
        }
    )


@router.get("/data-sources/health")
def data_sources_health(db: Session = Depends(get_db)):
    sources = db.query(m.DataSourceHealth).all()
    return ok(
        {
            "items": [
                {
                    "name": source.name,
                    "status": source.status,
                    "latency": f"{source.latency_ms}ms" if source.latency_ms < 1000 else f"{source.latency_ms / 1000:.1f}s",
                    "latencyMs": source.latency_ms,
                    "lastCheckedAt": dt_iso(source.last_checked_at),
                    "lastError": source.last_error,
                }
                for source in sources
            ]
        }
    )
