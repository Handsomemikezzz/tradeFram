from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ReviewEntryCreate, ReviewEntryUpdate, WeeklyReviewUpdate
from ..serializers_reviews import review_entry_payload, weekly_review_payload
from ..services.reviews import (
    create_review_entry,
    delete_review_entry,
    get_review_entry_or_404,
    get_stats_for_range,
    get_weekly_workbench,
    list_review_entries,
    save_weekly_review,
    update_review_entry,
)
from ..utils import ok

router = APIRouter()


@router.post("/reviews/entries")
def post_review_entry(payload: ReviewEntryCreate, db: Session = Depends(get_db)):
    return ok(review_entry_payload(create_review_entry(db, payload)))


@router.get("/reviews/entries")
def get_review_entries(
    startDate: date | None = None,
    endDate: date | None = None,
    entryType: str | None = None,
    actionType: str | None = None,
    code: str | None = None,
    planStatus: str | None = None,
    emotionTags: list[str] | None = Query(default=None),
    problemTags: list[str] | None = Query(default=None),
    sectorTags: list[str] | None = Query(default=None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = list_review_entries(
        db,
        start_date=startDate,
        end_date=endDate,
        entry_type=entryType,
        action_type=actionType,
        code=code,
        plan_status=planStatus,
        emotion_tags=emotionTags,
        problem_tags=problemTags,
        sector_tags=sectorTags,
        page=page,
        page_size=pageSize,
    )
    return ok({"items": [review_entry_payload(item) for item in items], "page": page, "pageSize": pageSize, "total": total, "hasMore": page * pageSize < total})


@router.get("/reviews/entries/{entry_id}")
def get_review_entry(entry_id: str, db: Session = Depends(get_db)):
    return ok(review_entry_payload(get_review_entry_or_404(db, entry_id)))


@router.patch("/reviews/entries/{entry_id}")
def patch_review_entry(entry_id: str, payload: ReviewEntryUpdate, db: Session = Depends(get_db)):
    return ok(review_entry_payload(update_review_entry(db, entry_id, payload)))


@router.delete("/reviews/entries/{entry_id}")
def remove_review_entry(entry_id: str, db: Session = Depends(get_db)):
    delete_review_entry(db, entry_id)
    return ok({"deleted": True})


@router.get("/reviews/stats")
def get_review_stats(startDate: date, endDate: date, db: Session = Depends(get_db)):
    return ok(get_stats_for_range(db, startDate, endDate))


@router.get("/reviews/weeks/{week_start}")
def get_review_week(week_start: date, db: Session = Depends(get_db)):
    workbench = get_weekly_workbench(db, week_start)
    return ok(
        {
            **workbench,
            "entries": [review_entry_payload(entry) for entry in workbench["entries"]],
            "planDeviationEntries": [review_entry_payload(entry) for entry in workbench["planDeviationEntries"]],
            "lowDisciplineEntries": [review_entry_payload(entry) for entry in workbench["lowDisciplineEntries"]],
            "weeklyReview": weekly_review_payload(workbench["weeklyReview"]),
        }
    )


@router.put("/reviews/weeks/{week_start}")
def put_review_week(week_start: date, payload: WeeklyReviewUpdate, db: Session = Depends(get_db)):
    return ok(weekly_review_payload(save_weekly_review(db, week_start, payload)))
