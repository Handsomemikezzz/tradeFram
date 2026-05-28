from __future__ import annotations

from . import models as m


def _list_payload(value: list | None) -> list:
    return list(value or [])


def review_entry_payload(entry: m.ReviewEntry) -> dict:
    return {
        "id": entry.id,
        "entryType": entry.entry_type,
        "actionType": entry.action_type,
        "tradeDate": entry.trade_date.isoformat(),
        "code": entry.code,
        "name": entry.name,
        "sectorTags": _list_payload(entry.sector_tags),
        "positionContext": entry.position_context,
        "planStatus": entry.plan_status,
        "emotionTags": _list_payload(entry.emotion_tags),
        "problemTags": _list_payload(entry.problem_tags),
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
        "linkedEntryIds": _list_payload(review.linked_entry_ids),
        "createdAt": review.created_at.isoformat(),
        "updatedAt": review.updated_at.isoformat(),
    }


def stock_review_event_payload(event: m.StockReviewEvent) -> dict:
    return {
        "id": event.id,
        "cardId": event.card_id,
        "eventDate": event.event_date.isoformat(),
        "eventType": event.event_type,
        "title": event.title,
        "reasonText": event.reason_text,
        "positionSnapshot": event.position_snapshot,
        "deviatedFromPlan": event.deviated_from_plan,
        "emotionTags": _list_payload(event.emotion_tags),
        "problemTags": _list_payload(event.problem_tags),
        "images": _list_payload(event.images),
        "createdAt": event.created_at.isoformat(),
        "updatedAt": event.updated_at.isoformat(),
    }


def stock_review_card_payload(card: m.StockReviewCard, *, include_events: bool = False) -> dict:
    payload = {
        "id": card.id,
        "status": card.status,
        "code": card.code,
        "name": card.name,
        "sectorTags": _list_payload(card.sector_tags),
        "startDate": card.start_date.isoformat(),
        "endDate": card.end_date.isoformat() if card.end_date else None,
        "initialAction": card.initial_action,
        "initialPositionContext": card.initial_position_context,
        "initialPlanStatus": card.initial_plan_status,
        "initialReasonText": card.initial_reason_text,
        "expectedMoveText": card.expected_move_text,
        "originalPlanText": card.original_plan_text,
        "initialEmotionTags": _list_payload(card.initial_emotion_tags),
        "problemTags": _list_payload(card.problem_tags),
        "sellReasonText": card.sell_reason_text,
        "pnlText": card.pnl_text,
        "followedPlan": card.followed_plan,
        "disciplineScore": card.discipline_score,
        "didWellText": card.did_well_text,
        "didWrongText": card.did_wrong_text,
        "reflectionText": card.reflection_text,
        "ruleText": card.rule_text,
        "initialImages": _list_payload(card.initial_images),
        "closeImages": _list_payload(card.close_images),
        
        # Professional Trading Audit Fields
        "strategyType": card.strategy_type,
        "expectedRrRatio": card.expected_rr_ratio,
        "stopLossTarget": card.stop_loss_target,
        "pnlAmount": card.pnl_amount,
        "rMultiple": card.r_multiple,
        "marketRegime": card.market_regime,
        "exitQuality": card.exit_quality,

        "createdAt": card.created_at.isoformat(),
        "updatedAt": card.updated_at.isoformat(),
    }
    if include_events:
        payload["events"] = [stock_review_event_payload(event) for event in card.events]
    return payload


def iron_law_payload(law: m.IronLaw) -> dict:
    return {
        "id": law.id,
        "text": law.text,
        "tag": law.tag,
        "status": law.status,
        "createdAt": law.created_at.isoformat(),
        "updatedAt": law.updated_at.isoformat(),
    }
