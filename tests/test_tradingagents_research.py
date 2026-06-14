from __future__ import annotations

from backend.app.services.tradingagents_research import (
    build_sections_from_final_state,
    map_a_share_to_yahoo_ticker,
    normalize_tradingagents_result,
)


def test_maps_a_share_code_to_yahoo_ticker():
    assert map_a_share_to_yahoo_ticker("600519") == "600519.SS"
    assert map_a_share_to_yahoo_ticker("688001") == "688001.SS"
    assert map_a_share_to_yahoo_ticker("000001") == "000001.SZ"
    assert map_a_share_to_yahoo_ticker("300750") == "300750.SZ"


def test_normalizes_tradingagents_final_state_for_report_display():
    final_state = {
        "market_report": "市场分析正文",
        "sentiment_report": "情绪分析正文",
        "news_report": "新闻分析正文",
        "fundamentals_report": "基本面分析正文",
        "investment_plan": "研究团队结论",
        "trader_investment_plan": "交易员计划",
        "past_context": "历史记忆上下文",
        "instrument_context": "标的识别信息",
        "investment_debate_state": {
            "bull_history": "看多论点",
            "bear_history": "看空论点",
            "history": "完整辩论记录",
            "judge_decision": "研究经理裁决",
        },
        "risk_debate_state": {
            "aggressive_history": "激进观点",
            "conservative_history": "保守观点",
            "neutral_history": "中性观点",
            "history": "风险辩论记录",
            "judge_decision": "风险裁决",
        },
        "final_trade_decision": (
            "Rating: Underweight\n\n"
            "Executive Summary: 立即减持 3-5 个百分点。\n\n"
            "Investment Thesis: 短期技术面破位，但长期结构未完全破坏。\n\n"
            "Price Target: 700.0\n\n"
            "Time Horizon: 1-3个月"
        ),
    }

    result = normalize_tradingagents_result(
        final_state=final_state,
        decision="Underweight",
        yahoo_ticker="600519.SS",
    )

    assert result["decision"]["rating"] == "Underweight"
    assert result["decision"]["executiveSummary"] == "立即减持 3-5 个百分点。"
    assert result["decision"]["investmentThesis"] == "短期技术面破位，但长期结构未完全破坏。"
    assert result["decision"]["priceTarget"] == "700.0"
    assert result["decision"]["timeHorizon"] == "1-3个月"
    assert result["decision"]["yahooTicker"] == "600519.SS"
    assert result["sections"]["market"] == "市场分析正文"
    assert result["sections"]["portfolioManager"] == final_state["final_trade_decision"]
    assert "看多论点" in result["sections"]["investmentDebate"]
    assert "激进观点" in result["sections"]["riskDebate"]
    assert result["sections"]["pastContext"] == "历史记忆上下文"
    assert "final_state" in result["raw"]


def test_build_sections_from_final_state_matches_normalize_sections():
    final_state = {
        "market_report": "市场",
        "investment_debate_state": {"bull_history": "bull"},
    }
    normalized = normalize_tradingagents_result(
        final_state=final_state,
        decision="Hold",
        yahoo_ticker="600519.SS",
    )
    rebuilt = build_sections_from_final_state(final_state)
    assert rebuilt["market"] == normalized["sections"]["market"]
    assert rebuilt["investmentDebate"] == normalized["sections"]["investmentDebate"]
