from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import ReviewEntryCreate, ReviewEntryUpdate, WeeklyReviewUpdate
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


def list_review_entries(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    entry_type: str | None = None,
    action_type: str | None = None,
    code: str | None = None,
    plan_status: str | None = None,
    emotion_tags: list[str] | None = None,
    problem_tags: list[str] | None = None,
    sector_tags: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[m.ReviewEntry], int]:
    query = db.query(m.ReviewEntry)
    if start_date:
        query = query.filter(m.ReviewEntry.trade_date >= start_date)
    if end_date:
        query = query.filter(m.ReviewEntry.trade_date <= end_date)
    if entry_type:
        query = query.filter(m.ReviewEntry.entry_type == entry_type)
    if action_type:
        query = query.filter(m.ReviewEntry.action_type == action_type)
    if code:
        query = query.filter(m.ReviewEntry.code == code)
    if plan_status:
        query = query.filter(m.ReviewEntry.plan_status == plan_status)

    all_items = query.order_by(desc(m.ReviewEntry.trade_date), desc(m.ReviewEntry.created_at)).all()
    filtered = [
        item
        for item in all_items
        if _contains_all(item.emotion_tags or [], emotion_tags)
        and _contains_all(item.problem_tags or [], problem_tags)
        and _contains_all(item.sector_tags or [], sector_tags)
    ]
    total = len(filtered)
    start = (page - 1) * page_size
    return filtered[start : start + page_size], total


def _contains_all(values: list[str], required: list[str] | None) -> bool:
    if not required:
        return True
    value_set = set(values)
    return all(item in value_set for item in required)


def build_review_stats(entries: list[m.ReviewEntry], start_date: date, end_date: date) -> dict:
    plan_counts = Counter(entry.plan_status for entry in entries)
    emotion_counts = Counter(tag for entry in entries for tag in (entry.emotion_tags or []))
    problem_counts = Counter(tag for entry in entries for tag in (entry.problem_tags or []))
    sector_counts = Counter(tag for entry in entries for tag in (entry.sector_tags or []))
    code_counts = Counter(entry.code for entry in entries if entry.code)
    scores = [entry.discipline_score for entry in entries]
    unplanned = plan_counts.get("UNPLANNED", 0) + plan_counts.get("INTRADAY_ADJUSTMENT", 0)
    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "totalCount": len(entries),
        "tradeActionCount": sum(1 for entry in entries if entry.entry_type == "TRADE_ACTION"),
        "observationDecisionCount": sum(1 for entry in entries if entry.entry_type == "OBSERVATION_DECISION"),
        "planStatusCounts": dict(plan_counts),
        "emotionTagCounts": dict(emotion_counts),
        "problemTagCounts": dict(problem_counts),
        "sectorTagCounts": dict(sector_counts),
        "codeCounts": dict(code_counts),
        "averageDisciplineScore": round(sum(scores) / len(scores), 2) if scores else None,
        "lowDisciplineCount": sum(1 for score in scores if score <= LOW_DISCIPLINE_SCORE_THRESHOLD),
        "lowDisciplineThreshold": LOW_DISCIPLINE_SCORE_THRESHOLD,
        "planDeviationRatio": round(unplanned / len(entries), 4) if entries else 0,
    }


def get_stats_for_range(db: Session, start_date: date, end_date: date) -> dict:
    entries, _ = list_review_entries(db, start_date=start_date, end_date=end_date, page=1, page_size=10000)
    return build_review_stats(entries, start_date, end_date)


def get_weekly_workbench(db: Session, week_start: date) -> dict:
    require_monday(week_start)
    end = week_end(week_start)
    entries, _ = list_review_entries(db, start_date=week_start, end_date=end, page=1, page_size=10000)
    review = db.query(m.WeeklyReview).filter(m.WeeklyReview.week_start == week_start).first()
    return {
        "weekStart": week_start.isoformat(),
        "weekEnd": end.isoformat(),
        "stats": build_review_stats(entries, week_start, end),
        "entries": entries,
        "planDeviationEntries": [entry for entry in entries if entry.plan_status in {"UNPLANNED", "INTRADAY_ADJUSTMENT"}],
        "lowDisciplineEntries": [entry for entry in entries if entry.discipline_score <= LOW_DISCIPLINE_SCORE_THRESHOLD],
        "weeklyReview": review,
    }


def save_weekly_review(db: Session, week_start: date, payload: WeeklyReviewUpdate) -> m.WeeklyReview:
    require_monday(week_start)
    missing = [entry_id for entry_id in payload.linkedEntryIds if db.get(m.ReviewEntry, entry_id) is None]
    if missing:
        raise api_error(422, "REVIEW_ENTRY_NOT_FOUND", "linkedEntryIds 包含不存在的复盘记录", {"missingIds": missing})
    review = db.query(m.WeeklyReview).filter(m.WeeklyReview.week_start == week_start).first()
    if review is None:
        review = m.WeeklyReview(id=new_id("wr"), week_start=week_start, week_end=week_end(week_start))
        db.add(review)
    review.summary_text = payload.summaryText
    review.repeated_mistakes_text = payload.repeatedMistakesText
    review.effective_actions_text = payload.effectiveActionsText
    review.emotion_pattern_text = payload.emotionPatternText
    review.next_week_focus_text = payload.nextWeekFocusText
    review.rule_candidates_text = payload.ruleCandidatesText
    review.linked_entry_ids = payload.linkedEntryIds
    review.updated_at = m.now_utc()
    db.commit()
    db.refresh(review)
    return review
