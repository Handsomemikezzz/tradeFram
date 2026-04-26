from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import EngineUpdate, PaperTradingRunCreate
from ..services.paper_trading import get_engine_state, run_paper_trading, set_engine_state, trading_time_mode
from ..utils import dt_iso, ok

router = APIRouter()


def engine_payload(state):
    return {
        "active": state.active,
        "mode": state.mode,
        "pollingEnabled": state.polling_enabled,
        "pollingIntervalSec": state.polling_interval_sec,
        "lastRunId": state.last_run_id,
        "updatedAt": dt_iso(state.updated_at),
        "tradingTimeMode": trading_time_mode(),
    }


@router.get("/paper-trading/engine")
def get_engine(db: Session = Depends(get_db)):
    return ok(engine_payload(get_engine_state(db)))


@router.patch("/paper-trading/engine")
def patch_engine(payload: EngineUpdate, db: Session = Depends(get_db)):
    state = set_engine_state(db, payload.active, payload.reason)
    data = engine_payload(state)
    data["message"] = "交易引擎已进入自动轮询状态" if state.active else "已断开与模拟下单服务的连接"
    return ok(data)


@router.post("/paper-trading/runs")
def create_run(payload: PaperTradingRunCreate, db: Session = Depends(get_db)):
    run = run_paper_trading(db, payload)
    return ok(
        {
            "runId": run.id,
            "status": run.status,
            "trigger": run.trigger,
            "summary": {k: v for k, v in run.summary.items() if k != "traceIds"},
            "traceIds": run.summary.get("traceIds", []),
            "startedAt": dt_iso(run.started_at),
            "finishedAt": dt_iso(run.finished_at),
        }
    )
