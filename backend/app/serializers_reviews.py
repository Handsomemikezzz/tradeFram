from __future__ import annotations

from . import models as m


def review_entry_payload(entry: m.ReviewEntry) -> dict:
    return {
        "id": entry.id,
        "entryType": entry.entry_type,
        "actionType": entry.action_type,
        "tradeDate": entry.trade_date.isoformat(),
        "code": entry.code,
        "name": entry.name,
        "sectorTags": entry.sector_tags or [],
        "positionContext": entry.position_context,
        "planStatus": entry.plan_status,
        "emotionTags": entry.emotion_tags or [],
        "problemTags": entry.problem_tags or [],
        "reasonText": entry.reason_text,
        "reflectionText": entry.reflection_text,
        "conclusionText": entry.conclusion_text,
        "nextActionText": entry.next_action_text,
        "disciplineScore": entry.discipline_score,
        "outcomeText": entry.outcome_text,
        "createdAt": entry.created_at.isoformat(),
        "updatedAt": entry.updated_at.isoformat(),
    }


def weekly_review_payload(review: m.WeeklyReview | None) -> dict | None:
    if review is None:
        return None
    return {
        "id": review.id,
        "weekStart": review.week_start.isoformat(),
        "weekEnd": review.week_end.isoformat(),
        "summaryText": review.summary_text,
        "repeatedMistakesText": review.repeated_mistakes_text,
        "effectiveActionsText": review.effective_actions_text,
        "emotionPatternText": review.emotion_pattern_text,
        "nextWeekFocusText": review.next_week_focus_text,
        "ruleCandidatesText": review.rule_candidates_text,
        "linkedEntryIds": review.linked_entry_ids or [],
        "createdAt": review.created_at.isoformat(),
        "updatedAt": review.updated_at.isoformat(),
    }
