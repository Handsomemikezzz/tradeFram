from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import ResearchTaskCreate
from ..utils import api_error, new_id


def require_stock(db: Session, code: str) -> m.Stock:
    stock = db.get(m.Stock, code)
    if stock is None:
        raise api_error(404, "STOCK_NOT_FOUND", f"股票 {code} 不存在于第一阶段 mock 数据")
    return stock


def create_research_task(db: Session, payload: ResearchTaskCreate) -> m.ResearchTask:
    stock = require_stock(db, payload.code)
    task_id = new_id("rt")
    report_id = new_id("rr")

    report = m.ResearchReport(
        id=report_id,
        task_id=task_id,
        code=stock.code,
        status="COMPLETED",
        overview=f"{stock.name}作为{stock.industry}板块的重要标的，当前第一阶段后端生成 mock 研究报告。报告仅用于研究学习和模拟交易，不构成投资建议。",
        key_insights=[
            f"行业属性：{stock.industry}，用于验证前端研究报告链路。",
            f"估值指标：PE {stock.pe}x，ROE {stock.roe}%。",
            "AI 仅生成研究报告，不直接决定交易，也不会直接创建订单。",
        ],
        risks=[
            {"title": "数据源限制", "description": "当前为 seed mock 数据，未接入 Tushare/AkShare。", "severity": "MEDIUM"},
            {"title": "模型限制", "description": "当前为 mock AI 报告，不能作为投资建议。", "severity": "HIGH"},
        ],
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
        data_completeness=0.98,
        ai_disclaimer="本报告由第一阶段 mock AI 生成，仅供研究学习与模拟交易演示，不构成投资建议。",
        data_sources=["SeedMock", "Local DB"],
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
