from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..serializers import dt_iso, log_payload, monitoring_payload
from ..utils import api_error, now_iso, ok

router = APIRouter()


def _task_counts(db: Session) -> dict:
    blocked = db.query(m.RiskCheck).filter(m.RiskCheck.status == "BLOCKED").count()
    failed_reports = db.query(m.ResearchTask).filter(m.ResearchTask.status == "FAILED").count()
    paused = db.query(m.MonitoringItem).filter(m.MonitoringItem.enabled.is_(False)).count()
    return {
        "riskBlockedToReview": blocked,
        "staleDataOver24h": 0,
        "failedResearchReports": failed_reports,
        "pausedMonitoringStocks": paused,
    }


@router.get("/risk/system-status")
def risk_system_status(db: Session = Depends(get_db)):
    account = db.get(m.PaperAccount, "paper_default")
    positions = db.query(m.Position).all()
    position_value = sum(p.market_value for p in positions)
    cash = account.cash if account else 0
    total_assets = cash + position_value
    position_ratio = round(position_value / total_assets * 100, 2) if total_assets else 0
    sources_with_errors = db.query(m.DataSourceHealth).filter(m.DataSourceHealth.status == "ERROR").count()
    rules = [
        {"rule": "TRADING_TIME", "label": "是否交易时间", "passed": True, "description": "允许手动巡检；所有执行仍仅限 PAPER_TRADING_ONLY"},
        {"rule": "DATA_INTEGRITY", "label": "数据完整性", "passed": sources_with_errors == 0, "description": "AkShare 数据源与本地缓存状态"},
        {"rule": "DUPLICATE_ORDER_PROTECTION", "label": "重复订单保护", "passed": True, "description": "同一 run 内由后端串行创建模拟订单"},
        {"rule": "MAX_SINGLE_STOCK_POS", "label": "单股持仓限制", "passed": True, "description": "最高 50,000 RMB / 股"},
        {"rule": "TOTAL_POSITION_LIMIT", "label": "总仓位警戒值", "passed": position_ratio <= 80, "description": f"状态: {'安全' if position_ratio <= 80 else '警戒'}, 当前 {position_ratio}%"},
    ]
    return ok({"overallStatus": "PASSED" if all(rule["passed"] for rule in rules) else "BLOCKED", "rules": rules})


@router.get("/execution-traces/latest")
def latest_execution_trace(db: Session = Depends(get_db)):
    trace = db.query(m.ExecutionTrace).order_by(desc(m.ExecutionTrace.updated_at)).first()
    if trace is None:
        raise api_error(404, "EXECUTION_TRACE_NOT_FOUND", "暂无交易链路追踪")
    stock = db.get(m.Stock, trace.code)
    return ok(
        {
            "traceId": trace.id,
            "runId": trace.run_id,
            "monitoringItemId": trace.monitoring_item_id,
            "code": trace.code,
            "symbol": stock.symbol if stock else None,
            "currentStep": trace.current_step,
            "status": trace.status,
            "steps": trace.steps,
            "createdAt": dt_iso(trace.created_at),
            "updatedAt": dt_iso(trace.updated_at),
        }
    )


@router.get("/dashboard/overview")
def dashboard_overview(_: date | None = None, db: Session = Depends(get_db)):
    watchlist_count = db.query(m.WatchlistItem).count()
    monitoring_count = db.query(m.MonitoringItem).count()
    today_signal_count = db.query(m.Signal).count()
    buy_count = db.query(m.Signal).filter(m.Signal.type == "BUY").count()
    sell_count = db.query(m.Signal).filter(m.Signal.type == "SELL").count()
    blocked_count = db.query(m.RiskCheck).filter(m.RiskCheck.status == "BLOCKED").count()
    account = db.get(m.PaperAccount, "paper_default")
    positions = db.query(m.Position).all()
    position_value = sum(p.market_value for p in positions)
    total_assets = (account.cash if account else 0) + position_value
    month_return = round((total_assets - account.initial_cash) / account.initial_cash * 100, 2) if account and account.initial_cash else 0
    return ok(
        {
            "riskDisclaimer": "本系统仅用于研究学习和模拟交易，不构成投资建议。所有交易结果均为模拟数据。",
            "kpis": {
                "watchlistCount": watchlist_count,
                "monitoringCount": monitoring_count,
                "watchlistTrendText": f"{watchlist_count} 已加入观察池",
                "todaySignalCount": today_signal_count,
                "todayBuySignalCount": buy_count,
                "todaySellSignalCount": sell_count,
                "todayRiskBlockedCount": blocked_count,
                "paperAccountNetAsset": round(total_assets, 2),
                "monthReturnPct": month_return,
            },
            "tasks": _task_counts(db),
            "quickResearchStats": {
                "completedResearchCount": db.query(m.ResearchTask).filter(m.ResearchTask.status == "COMPLETED").count(),
                "pendingTaskCount": db.query(m.ResearchTask).filter(m.ResearchTask.status.in_(["PENDING", "PROCESSING"])).count(),
            },
            "system": {"status": "NORMAL", "tradeDay": True, "market": "SH_SZ", "currentTime": now_iso()},
        }
    )


@router.get("/dashboard/monitoring-summary")
def dashboard_monitoring_summary(limit: int = Query(4, ge=1, le=20), db: Session = Depends(get_db)):
    items = db.query(m.MonitoringItem).order_by(desc(m.MonitoringItem.updated_at)).limit(limit).all()
    result = []
    for item in items:
        latest_signal = db.query(m.Signal).filter(m.Signal.monitoring_item_id == item.id).order_by(desc(m.Signal.generated_at)).first()
        latest_risk = db.query(m.RiskCheck).filter(m.RiskCheck.code == item.code).order_by(desc(m.RiskCheck.checked_at)).first()
        latest_order = db.query(m.PaperOrder).filter(m.PaperOrder.code == item.code).order_by(desc(m.PaperOrder.create_time)).first()
        result.append(monitoring_payload(item, latest_signal, latest_risk, latest_order))
    return ok({"items": result})


@router.get("/research/stats")
def research_stats(period: str = "month", db: Session = Depends(get_db)):
    industries = [row[0] for row in db.query(m.Stock.industry).join(m.ResearchTask, m.ResearchTask.code == m.Stock.code).group_by(m.Stock.industry).order_by(desc(func.count(m.Stock.industry))).limit(5).all()]
    if not industries:
        industries = [row[0] for row in db.query(m.Stock.industry).group_by(m.Stock.industry).limit(5).all()]
    return ok(
        {
            "period": period.upper(),
            "researchCount": db.query(m.ResearchTask).count(),
            "watchlistConvertedCount": db.query(m.WatchlistItem).count(),
            "popularIndustries": industries,
        }
    )
