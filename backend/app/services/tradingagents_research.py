from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .data_service import normalize_stock_code


SECTION_KEYS = {
    "market": "market_report",
    "sentiment": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
    "researchTeam": "investment_plan",
    "trader": "trader_investment_plan",
    "portfolioManager": "final_trade_decision",
}


def map_a_share_to_yahoo_ticker(raw_code: str) -> str:
    code, _, exchange = normalize_stock_code(raw_code)
    if exchange == "SH":
        return f"{code}.SS"
    if exchange == "SZ":
        return f"{code}.SZ"
    if exchange == "BJ":
        return f"{code}.BJ"
    return f"{code}.SS"


def build_sections_from_final_state(final_state: dict[str, Any]) -> dict[str, str]:
    sections = {
        section_name: _string_value(final_state.get(state_key))
        for section_name, state_key in SECTION_KEYS.items()
    }
    sections["pastContext"] = _string_value(final_state.get("past_context"))
    sections["instrumentContext"] = _string_value(final_state.get("instrument_context"))
    sections["investmentDebate"] = _format_investment_debate(final_state.get("investment_debate_state"))
    sections["riskDebate"] = _format_risk_debate(final_state.get("risk_debate_state"))
    return sections


def normalize_tradingagents_result(
    *,
    final_state: dict[str, Any],
    decision: str,
    yahoo_ticker: str,
) -> dict[str, Any]:
    final_decision = _string_value(final_state.get("final_trade_decision"))
    parsed = _parse_portfolio_decision(final_decision)
    rating = decision or parsed.get("rating") or "Unknown"
    sections = build_sections_from_final_state(final_state)
    return {
        "decision": {
            "rating": rating,
            "executiveSummary": parsed.get("executiveSummary") or final_decision,
            "investmentThesis": parsed.get("investmentThesis") or "",
            "priceTarget": parsed.get("priceTarget") or "",
            "timeHorizon": parsed.get("timeHorizon") or "",
            "yahooTicker": yahoo_ticker,
        },
        "sections": sections,
        "raw": {
            # TradingAgents state can contain message objects; stringify unknowns so SQLite JSON can persist it.
            "final_state": _json_safe(final_state),
            "decision": decision,
        },
    }


def run_tradingagents_analysis(
    *,
    raw_code: str,
    analysis_date: date | str,
    output_language: str = "Chinese",
) -> dict[str, Any]:
    _ensure_tradingagents_import_path()
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    yahoo_ticker = map_a_share_to_yahoo_ticker(raw_code)
    config = DEFAULT_CONFIG.copy()
    config["output_language"] = output_language
    final_state, decision = TradingAgentsGraph(debug=False, config=config).propagate(
        yahoo_ticker,
        analysis_date.isoformat() if isinstance(analysis_date, date) else analysis_date,
    )
    return normalize_tradingagents_result(
        final_state=final_state,
        decision=str(decision),
        yahoo_ticker=yahoo_ticker,
    )


def _ensure_tradingagents_import_path() -> None:
    configured = os.getenv("TRADINGAGENTS_PROJECT_PATH")
    candidates = [Path(configured).expanduser()] if configured else []
    # Local development default: waytofree and TradingAgents are sibling-ish repos under codeMIni-hn.
    candidates.append(Path(__file__).resolve().parents[6] / "github" / "TradingAgents")
    for candidate in candidates:
        if candidate and (candidate / "tradingagents").exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
            return


def _format_investment_debate(state: Any) -> str:
    if not isinstance(state, dict):
        return ""
    parts: list[str] = []
    bull = _string_value(state.get("bull_history")).strip()
    bear = _string_value(state.get("bear_history")).strip()
    history = _string_value(state.get("history")).strip()
    judge = _string_value(state.get("judge_decision")).strip()
    if bull:
        parts.append(f"### Bull Researcher\n\n{bull}")
    if bear:
        parts.append(f"### Bear Researcher\n\n{bear}")
    if history:
        parts.append(f"### Debate Transcript\n\n{history}")
    if judge:
        parts.append(f"### Research Manager\n\n{judge}")
    return "\n\n".join(parts)


def _format_risk_debate(state: Any) -> str:
    if not isinstance(state, dict):
        return ""
    parts: list[str] = []
    aggressive = _string_value(state.get("aggressive_history")).strip()
    conservative = _string_value(state.get("conservative_history")).strip()
    neutral = _string_value(state.get("neutral_history")).strip()
    history = _string_value(state.get("history")).strip()
    judge = _string_value(state.get("judge_decision")).strip()
    if aggressive:
        parts.append(f"### Aggressive Analyst\n\n{aggressive}")
    if conservative:
        parts.append(f"### Conservative Analyst\n\n{conservative}")
    if neutral:
        parts.append(f"### Neutral Analyst\n\n{neutral}")
    if history:
        parts.append(f"### Risk Debate Transcript\n\n{history}")
    if judge:
        parts.append(f"### Risk Judge\n\n{judge}")
    return "\n\n".join(parts)


def _parse_portfolio_decision(markdown: str) -> dict[str, str]:
    labels = {
        "rating": "Rating",
        "executiveSummary": "Executive Summary",
        "investmentThesis": "Investment Thesis",
        "priceTarget": "Price Target",
        "timeHorizon": "Time Horizon",
    }
    result: dict[str, str] = {}
    for field, label in labels.items():
        value = _extract_labeled_block(markdown, label, labels.values())
        if value:
            result[field] = value
    return result


def _extract_labeled_block(markdown: str, label: str, all_labels) -> str | None:
    label_pattern = re.escape(label)
    other_labels = "|".join(re.escape(item) for item in all_labels if item != label)
    match = re.search(
        rf"(?:^|\n)\s*(?:\*\*)?{label_pattern}(?:\*\*)?\s*:\s*(.*?)(?=\n\s*(?:\*\*)?(?:{other_labels})(?:\*\*)?\s*:|\Z)",
        markdown,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    return match.group(1).strip()


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)
