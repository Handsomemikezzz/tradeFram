from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from .. import models as m
from ..database import SessionLocal
from ..schemas import ResearchTaskCreate
from ..utils import api_error, new_id
from .data_service import DataFetchError, fetch_market_dataset, get_provider, normalize_stock_code
from .tradingagents_research import run_tradingagents_analysis


def require_stock(db: Session, code: str) -> m.Stock:
    normalized_code = normalize_stock_code(code)[0]
    stock = db.get(m.Stock, normalized_code)
    if stock is None:
        raise api_error(404, "STOCK_NOT_FOUND", f"股票 {code} 不存在于本地数据")
    return stock


def create_research_task(db: Session, payload: ResearchTaskCreate) -> m.ResearchTask:
    task_id = new_id("rt")
    code = normalize_stock_code(payload.code)[0]
    task = m.ResearchTask(
        id=task_id,
        code=code,
        status="PROCESSING",
        current_step="FETCH_MARKET_DATA",
        progress_pct=5,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def run_research_task(task_id: str, payload_data: dict) -> None:
    db = SessionLocal()
    try:
        payload = ResearchTaskCreate.model_validate(payload_data)
        _run_research_task(db, task_id, payload)
    finally:
        db.close()


def _run_research_task(db: Session, task_id: str, payload: ResearchTaskCreate) -> None:
    task = db.get(m.ResearchTask, task_id)
    if task is None:
        return
    provider_name = payload.options.get("provider") if payload.options else None
    try:
        _update_task(db, task, "PROCESSING", "FETCH_MARKET_DATA", 15)
        market_dataset = fetch_market_dataset(db, payload.code, provider=get_provider(provider_name))
    except DataFetchError as exc:
        _fail_task(db, task, exc.message, "FETCH_MARKET_DATA")
        return
    except Exception as exc:
        _fail_task(db, task, str(exc), "FETCH_MARKET_DATA")
        return

    stock = market_dataset["stock"]
    bars = market_dataset["bars"]
    financial = market_dataset.get("financial")
    from .indicators import moving_average_snapshot_from_bars

    indicator = moving_average_snapshot_from_bars(bars)
    latest_close = indicator.latest_close if indicator.latest_close is not None else stock.price
    ma5 = indicator.ma5 if indicator.ma5 is not None else stock.price
    ma20 = indicator.ma20 if indicator.ma20 is not None else stock.price

    try:
        _update_task(db, task, "PROCESSING", "RUN_TRADING_AGENTS", 45)
        ai_result = run_tradingagents_analysis(
            raw_code=stock.code,
            analysis_date=_analysis_date(payload),
            output_language=str((payload.options or {}).get("outputLanguage") or "Chinese"),
        )
    except Exception as exc:
        _fail_task(db, task, str(exc), "RUN_TRADING_AGENTS")
        return

    _update_task(db, task, "PROCESSING", "NORMALIZE_REPORT", 85)
    decision = ai_result["decision"]
    report_id = new_id("rr")
    risks = [
        {"title": "模型输出限制", "description": "TradingAgents 输出受模型、采样、数据源与提示词影响，不能作为投资建议或自动下单依据。", "severity": "HIGH"},
        {"title": "数据源限制", "description": "行情与财务摘要来自公开数据源；上游不可用时任务会显式失败或沿用已标记的过期缓存。", "severity": "MEDIUM"},
    ]
    if market_dataset.get("dataStale"):
        risks.insert(
            0,
            {
                "title": "缓存数据可能过期",
                "description": f"刷新外部数据源失败，当前报告沿用本地缓存。原因：{market_dataset.get('refreshError') or '未知'}",
                "severity": "MEDIUM",
            },
        )
    report = m.ResearchReport(
        id=report_id,
        task_id=task_id,
        code=stock.code,
        status="COMPLETED",
        overview=decision.get("executiveSummary") or f"{stock.name}（{stock.symbol}）TradingAgents 研究报告已生成。",
        key_insights=_build_key_insights(stock, market_dataset, latest_close, ma5, ma20, decision),
        risks=risks,
        business_segments=[],
        news_items=[],
        worth_further_research=True,
        ai_confidence=0.8,
        data_completeness=market_dataset["dataCompleteness"],
        ai_disclaimer="本报告由 TradingAgents 基于公开数据和大语言模型生成，仅用于个人研究与复盘，不构成投资建议。",
        research_base_period=financial.report_period if financial else "UNKNOWN",
        data_sources=[*market_dataset["dataSources"], "TradingAgents"],
        ai_decision=decision,
        ai_raw_result={"sections": ai_result["sections"], "raw": ai_result["raw"]},
    )
    db.add(report)
    task.status = "COMPLETED"
    task.current_step = "DONE"
    task.progress_pct = 100
    task.error_message = None
    task.report_id = report_id
    db.add(task)
    db.add(
        m.SystemLog(
            id=new_id("log"),
            level="SUCCESS",
            module="AI",
            code=stock.code,
            event="TradingAgents 报告生成",
            detail=f"{stock.name} TradingAgents 研究报告生成完毕，评级：{decision.get('rating') or 'Unknown'}",
            rel_id=report_id,
        )
    )
    db.commit()


def _build_key_insights(stock: m.Stock, market_dataset: dict, latest_close: float, ma5: float, ma20: float, decision: dict | None = None) -> list[str]:
    insights = [
        f"行业属性：{stock.industry}；数据源：{' / '.join(market_dataset['dataSources'])}。",
        f"最新收盘价：{latest_close:.2f}；MA5={ma5:.2f}，MA20={ma20:.2f}。",
    ]
    if decision:
        insights.append(f"TradingAgents 评级：{decision.get('rating') or 'Unknown'}；目标价：{decision.get('priceTarget') or '未给出'}；周期：{decision.get('timeHorizon') or '未给出'}。")
        if decision.get("investmentThesis"):
            insights.append(f"投资论点：{decision['investmentThesis']}")
    financial = market_dataset.get("financial")
    if financial is not None:
        insights.append(f"财务摘要：ROE {stock.roe}%，营业收入 {stock.revenue}，归母净利润 {stock.profit}。")
    else:
        insights.append("AkShare 当前未返回可用财务摘要。")
    if market_dataset.get("dataStale"):
        insights.append(f"当前使用过期缓存；最近刷新错误：{market_dataset.get('refreshError') or '未知'}。")
    return insights


def _analysis_date(payload: ResearchTaskCreate) -> date:
    raw = (payload.options or {}).get("analysisDate")
    if raw:
        return date.fromisoformat(str(raw))
    return date.today()


def _update_task(db: Session, task: m.ResearchTask, status: str, step: str, progress: int) -> None:
    task.status = status
    task.current_step = step
    task.progress_pct = progress
    task.updated_at = m.now_utc()
    db.add(task)
    db.commit()


def _fail_task(db: Session, task: m.ResearchTask, message: str, step: str) -> None:
    task.status = "FAILED"
    task.current_step = step
    task.progress_pct = max(task.progress_pct, 1)
    task.error_message = message
    task.updated_at = m.now_utc()
    db.add(task)
    db.add(
        m.SystemLog(
            id=new_id("log"),
            level="ERROR",
            module="Research",
            code=task.code,
            event="研究任务失败",
            detail=message,
            rel_id=task.id,
        )
    )
    db.commit()
