from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..schemas import ResearchTaskCreate
from ..serializers import research_record_payload, research_report_payload, research_task_payload
from ..services.research import create_research_task, delete_research_task, run_research_task
from ..utils import api_error, ok

router = APIRouter()


@router.post("/research/tasks")
def create_task(payload: ResearchTaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = create_research_task(db, payload)
    background_tasks.add_task(run_research_task, task.id, payload.model_dump(mode="json"))
    return ok(research_task_payload(task))


@router.delete("/research/tasks/{taskId}")
def delete_task(taskId: str, db: Session = Depends(get_db)):
    delete_research_task(db, taskId)
    return ok({"deleted": True})


@router.get("/research/tasks/{taskId}")
def get_task(taskId: str, db: Session = Depends(get_db)):
    task = db.get(m.ResearchTask, taskId)
    if task is None:
        raise api_error(404, "RESEARCH_TASK_NOT_FOUND", f"研究任务 {taskId} 不存在")
    return ok(research_task_payload(task))


@router.get("/research/reports/by-code/{code}")
def get_report_by_code(code: str, db: Session = Depends(get_db)):
    report = db.query(m.ResearchReport).filter(m.ResearchReport.code == code).order_by(desc(m.ResearchReport.generated_at)).first()
    if report is None:
        raise api_error(404, "REPORT_NOT_FOUND", f"股票 {code} 暂无研究报告")
    return ok(research_report_payload(report))


@router.get("/research/records")
def get_research_records(
    status: str | None = None,
    keyword: str | None = None,
    code: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(m.ResearchTask).join(m.Stock)
    if status:
        query = query.filter(m.ResearchTask.status == status)
    if code:
        query = query.filter(m.ResearchTask.code == code)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((m.ResearchTask.code.like(like)) | (m.Stock.name.like(like)))
    total = query.count()
    items = query.order_by(desc(m.ResearchTask.created_at)).offset((page - 1) * pageSize).limit(pageSize).all()
    return ok({"items": [research_record_payload(item) for item in items], "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})
