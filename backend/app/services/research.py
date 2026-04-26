from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import ResearchTaskCreate
from ..utils import api_error, new_id
from .data_service import DataFetchError, fetch_market_dataset, get_provider, normalize_stock_code


def require_stock(db: Session, code: str) -> m.Stock:
    normalized_code = normalize_stock_code(code)[0]
    stock = db.get(m.Stock, normalized_code)
    if stock is None:
        raise api_error(404, "STOCK_NOT_FOUND", f"股票 {code} 不存在于本地数据")
    return stock


def create_research_task(db: Session, payload: ResearchTaskCreate) -> m.ResearchTask:
    task_id = new_id("rt")
    report_id = new_id("rr")
    provider_name = payload.options.get("provider") if payload.options else None
    try:
        market_dataset = fetch_market_dataset(db, payload.code, provider=None if provider_name is None else get_provider(provider_name))
    except DataFetchError as exc:
        task = m.ResearchTask(
            id=task_id,
            code=normalize_stock_code(payload.code)[0],
            status="FAILED",
            current_step="FETCH_MARKET_DATA",
            progress_pct=20,
            error_message=exc.message,
        )
        db.add(task)
        db.add(
            m.SystemLog(
                id=new_id("log"),
                level="ERROR",
                module="Research",
                code=task.code,
                event="研究任务失败",
                detail=exc.message,
                rel_id=task_id,
            )
        )
        db.commit()
        raise api_error(exc.status_code, exc.code, exc.message, exc.details) from exc

    stock = market_dataset["stock"]
    bars = market_dataset["bars"]
    latest_close = bars[-1].close if bars else stock.price
    ma5 = sum(bar.close for bar in bars[-5:]) / min(len(bars), 5)
    ma20 = sum(bar.close for bar in bars[-20:]) / min(len(bars), 20)

    risks = [
        {"title": "数据源限制", "description": "v0.1 Beta+ 仅按单只股票拉取基础数据；默认使用可复现 MockProvider，AkShare 为可选真实数据源。", "severity": "MEDIUM"},
        {"title": "模型限制", "description": "当前为模板化 mock AI 报告，不能作为投资建议。", "severity": "HIGH"},
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
        overview=f"{stock.name}作为{stock.industry}板块的重要标的，v0.1 Beta 已接入统一行情数据层。本报告基于最近 {len(bars)} 条日线数据、基础财务摘要和模板化 mock AI 生成，仅用于研究学习和模拟交易，不构成投资建议。",
        key_insights=[
            f"行业属性：{stock.industry}，数据源：{' / '.join(market_dataset['dataSources'])}。",
            f"最新收盘价：{latest_close:.2f}，MA5={ma5:.2f}，MA20={ma20:.2f}。",
            f"估值指标：PE {stock.pe}x，ROE {stock.roe}%。",
            "AI 仅生成研究报告，不直接决定交易，也不会直接创建订单。",
        ],
        risks=risks,
        business_segments=[
            {"name": stock.industry, "percent": 80.0},
            {"name": "相关业务", "percent": 15.0},
            {"name": "其他业务", "percent": 5.0},
        ],
        news_items=[
            {"id": new_id("news"), "title": f"{stock.name} mock 研究资讯", "date": "2026-04-25", "type": "NEWS", "url": None},
            {"id": new_id("ann"), "title": f"{stock.name} mock 公告摘要", "date": "2026-04-24", "type": "ANNOUNCEMENT", "url": None},
        ],
        worth_further_research=True,
        ai_confidence=0.92,
        data_completeness=market_dataset["dataCompleteness"],
        ai_disclaimer="本报告由 v0.1 Beta 模板化 mock AI 生成；AI 只生成研究报告，不直接下单，不构成投资建议。",
        data_sources=market_dataset["dataSources"],
    )
    task = m.ResearchTask(
        id=task_id,
        code=stock.code,
        status="COMPLETED",
        current_step="DONE",
        progress_pct=100,
        report_id=report_id,
    )
    db.add(report)
    db.add(task)
    db.add(
        m.SystemLog(
            id=new_id("log"),
            level="SUCCESS",
            module="AI",
            code=stock.code,
            event="报告生成",
            detail=f"{stock.name} mock 研究报告生成完毕",
            rel_id=report_id,
        )
    )
    db.commit()
    db.refresh(task)
    return task
