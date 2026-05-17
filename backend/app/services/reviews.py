from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import ReviewEntryCreate, ReviewEntryUpdate
from ..utils import api_error, new_id

LOW_DISCIPLINE_SCORE_THRESHOLD = 2


def week_end(week_start: date) -> date:
    return week_start + timedelta(days=6)


def require_monday(value: date) -> None:
    if value.weekday() != 0:
        raise api_error(422, "INVALID_WEEK_START", "weekStart 必须是周一")


def create_review_entry(db: Session, payload: ReviewEntryCreate) -> m.ReviewEntry:
    entry = m.ReviewEntry(
        id=new_id("rv"),
        entry_type=payload.entryType,
        action_type=payload.actionType,
        trade_date=payload.tradeDate,
        code=payload.code,
        name=payload.name,
        sector_tags=payload.sectorTags,
        position_context=payload.positionContext,
        plan_status=payload.planStatus,
        emotion_tags=payload.emotionTags,
        problem_tags=payload.problemTags,
        reason_text=payload.reasonText,
        reflection_text=payload.reflectionText,
        conclusion_text=payload.conclusionText,
        next_action_text=payload.nextActionText,
        discipline_score=payload.disciplineScore,
        outcome_text=payload.outcomeText,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_review_entry_or_404(db: Session, entry_id: str) -> m.ReviewEntry:
    entry = db.get(m.ReviewEntry, entry_id)
    if entry is None:
        raise api_error(404, "REVIEW_ENTRY_NOT_FOUND", f"复盘记录 {entry_id} 不存在")
    return entry


def update_review_entry(db: Session, entry_id: str, payload: ReviewEntryUpdate) -> m.ReviewEntry:
    entry = get_review_entry_or_404(db, entry_id)
    data = payload.model_dump(exclude_unset=True)
    field_map = {
        "entryType": "entry_type",
        "actionType": "action_type",
        "tradeDate": "trade_date",
        "sectorTags": "sector_tags",
        "positionContext": "position_context",
        "planStatus": "plan_status",
        "emotionTags": "emotion_tags",
        "problemTags": "problem_tags",
        "reasonText": "reason_text",
        "reflectionText": "reflection_text",
        "conclusionText": "conclusion_text",
        "nextActionText": "next_action_text",
        "disciplineScore": "discipline_score",
        "outcomeText": "outcome_text",
    }
    for key, value in data.items():
        setattr(entry, field_map.get(key, key), value)
    entry.updated_at = m.now_utc()
    db.commit()
    db.refresh(entry)
    return entry


def delete_review_entry(db: Session, entry_id: str) -> None:
    entry = get_review_entry_or_404(db, entry_id)
    db.delete(entry)
    db.commit()
