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
        market_dataset = fetch_market_dataset(db, payload.code, provider=get_provider(provider_name))
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
    financial = market_dataset.get("financial")
    from .indicators import moving_average_snapshot_from_bars

    indicator = moving_average_snapshot_from_bars(bars)
    latest_close = indicator.latest_close if indicator.latest_close is not None else stock.price
    ma5 = indicator.ma5 if indicator.ma5 is not None else stock.price
    ma20 = indicator.ma20 if indicator.ma20 is not None else stock.price

    risks = [
        {"title": "数据源限制", "description": "当前仅通过 AkShare 按单只股票拉取公开行情与财务摘要；上游不可用时任务会显式失败或沿用已标记的过期缓存。", "severity": "MEDIUM"},
        {"title": "研究限制", "description": "当前未接入真实 AI 推理与人工投研校验，报告仅整理 AkShare 已返回的数据，不构成投资建议。", "severity": "HIGH"},
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
        overview=f"{stock.name}（{stock.symbol}）属于{stock.industry}行业。本报告基于 AkShare 返回的最近 {len(bars)} 条日线行情与可用财务摘要整理生成。",
        key_insights=_build_key_insights(stock, market_dataset, latest_close, ma5, ma20),
        risks=risks,
        business_segments=[],
        news_items=[],
        worth_further_research=True,
        ai_confidence=0.0,
        data_completeness=market_dataset["dataCompleteness"],
        ai_disclaimer="本报告仅整理 AkShare 返回的公开数据；当前未接入真实 AI 推理、真实券商或人工投研校验，不构成投资建议。",
        research_base_period=financial.report_period if financial else "UNKNOWN",
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
            detail=f"{stock.name} AkShare 数据研究报告生成完毕",
            rel_id=report_id,
        )
    )
    db.commit()
    db.refresh(task)
    return task


def _build_key_insights(stock: m.Stock, market_dataset: dict, latest_close: float, ma5: float, ma20: float) -> list[str]:
    insights = [
        f"行业属性：{stock.industry}；数据源：{' / '.join(market_dataset['dataSources'])}。",
        f"最新收盘价：{latest_close:.2f}；MA5={ma5:.2f}，MA20={ma20:.2f}。",
    ]
    financial = market_dataset.get("financial")
    if financial is not None:
        insights.append(f"财务摘要：ROE {stock.roe}%，营业收入 {stock.revenue}，归母净利润 {stock.profit}。")
    else:
        insights.append("AkShare 当前未返回可用财务摘要。")
    if market_dataset.get("dataStale"):
        insights.append(f"当前使用过期缓存；最近刷新错误：{market_dataset.get('refreshError') or '未知'}。")
    return insights
