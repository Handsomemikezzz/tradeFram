from __future__ import annotations

from datetime import timedelta

from sqlalchemy import desc
from sqlalchemy.orm import object_session

from . import models as m
from .data_layer.warehouse.reader import WarehouseMarketDataStore
from .services.tradingagents_research import build_sections_from_final_state
from .utils import dt_iso


def stock_payload(stock: m.Stock) -> dict:
    return {
        "code": stock.code,
        "symbol": stock.symbol,
        "exchange": stock.exchange,
        "name": stock.name,
        "market": stock.market,
        "industry": stock.industry,
    }


def quote_payload(stock: m.Stock) -> dict:
    live = _live_quote_from_warehouse(stock)
    if live is not None:
        return live
    return {
        "price": stock.price,
        "change": stock.change,
        "changePercent": stock.change_percent,
        "volume": stock.volume,
        "amount": stock.amount,
        "updateTime": dt_iso(stock.update_time),
    }


def _live_quote_from_warehouse(stock: m.Stock) -> dict | None:
    store = WarehouseMarketDataStore()
    latest = store.latest_bar(stock.code)
    if latest is None:
        return None
    previous = store.get_daily_bars(stock.code, end_date=latest.trade_date - timedelta(days=1), limit=1)
    prev = previous[-1] if previous else None
    change = round(latest.close - prev.close, 2) if prev else stock.change
    change_percent = round((change / prev.close) * 100, 2) if prev and prev.close else stock.change_percent
    return {
        "price": latest.close,
        "change": change,
        "changePercent": change_percent,
        "volume": latest.volume,
        "amount": latest.amount,
        "updateTime": dt_iso(latest.fetched_at),
    }


def _merge_live_price_insights(key_insights: list[str], stock: m.Stock) -> list[str]:
    from .services.indicators import moving_average_snapshot_for_code

    snapshot = moving_average_snapshot_for_code(stock.code)
    if snapshot.latest_close is None or snapshot.ma5 is None or snapshot.ma20 is None:
        return key_insights
    live_line = f"最新收盘价：{snapshot.latest_close:.2f}；MA5={snapshot.ma5:.2f}，MA20={snapshot.ma20:.2f}。"
    merged: list[str] = []
    replaced = False
    for insight in key_insights:
        if insight.startswith("最新收盘价："):
            merged.append(live_line)
            replaced = True
        else:
            merged.append(insight)
    if not replaced:
        merged.insert(1, live_line)
    return merged


def research_task_payload(task: m.ResearchTask) -> dict:
    return {
        "taskId": task.id,
        "code": task.code,
        "symbol": task.stock.symbol if task.stock else None,
        "status": task.status,
        "currentStep": task.current_step,
        "progressPct": task.progress_pct,
        "errorMessage": task.error_message,
        "createdAt": dt_iso(task.created_at),
        "updatedAt": dt_iso(task.updated_at),
        "reportId": task.report_id,
        "redirectTo": f"/research/{task.code}" if task.report_id else None,
    }


def research_record_payload(task: m.ResearchTask) -> dict:
    return {
        "id": task.id,
        "taskId": task.id,
        "reportId": task.report_id,
        "code": task.code,
        "symbol": task.stock.symbol,
        "name": task.stock.name,
        "researchTime": dt_iso(task.created_at),
        "status": task.status,
        "updateTime": dt_iso(task.updated_at),
    }


def research_report_payload(report: m.ResearchReport) -> dict:
    stock = report.stock
    latest_quote = getattr(stock, "update_time", None)
    provider = report.data_sources[0] if report.data_sources else "UNKNOWN"
    used_cache = "Local Cache" in report.data_sources
    data_stale = "Stale Cache" in report.data_sources
    financial = _latest_financial(report)
    return {
        "reportId": report.id,
        "code": report.code,
        "symbol": stock.symbol,
        "name": stock.name,
        "market": stock.market,
        "industry": stock.industry,
        "generatedAt": dt_iso(report.generated_at),
        "researchBasePeriod": report.research_base_period,
        "dataSources": report.data_sources,
        "dataUpdatedAt": dt_iso(latest_quote or report.generated_at),
        "dataMeta": {
            "provider": provider,
            "usedCache": used_cache,
            "dataStale": data_stale,
            "dataCompleteness": report.data_completeness,
            "lastError": _last_data_error(report),
        },
        "updateFrequency": "10min",
        "quote": quote_payload(stock),
        "trend": trend_payload(stock),
        "financialSnapshot": financial_snapshot_payload(financial) if financial else None,
        "tradingAgentsDecision": report.ai_decision or None,
        "tradingAgentsSections": _trading_agents_sections(report),
        "report": {
            "overview": report.overview,
            "keyInsights": _merge_live_price_insights(report.key_insights, stock),
            "worthFurtherResearch": report.worth_further_research,
            "aiConfidence": None,
            "dataCompleteness": report.data_completeness,
            "aiDisclaimer": report.ai_disclaimer,
            "risks": report.risks,
            "businessSegments": report.business_segments,
            "newsItems": report.news_items,
        },
    }


def _trading_agents_sections(report: m.ResearchReport) -> dict:
    raw_result = report.ai_raw_result or {}
    final_state = (raw_result.get("raw") or {}).get("final_state")
    if isinstance(final_state, dict) and final_state:
        return build_sections_from_final_state(final_state)
    return raw_result.get("sections") or {}


def financial_snapshot_payload(financial: m.FinancialSnapshot) -> dict:
    return {
        "revenue": financial.revenue,
        "profit": financial.profit,
        "grossMargin": financial.gross_margin,
        "netMargin": financial.net_margin,
        "roe": financial.roe,
        "pe": financial.pe,
    }


def _latest_financial(report: m.ResearchReport) -> m.FinancialSnapshot | None:
    session = object_session(report)
    if session is None or not report.data_sources:
        return None
    return (
        session.query(m.FinancialSnapshot)
        .filter(m.FinancialSnapshot.code == report.code, m.FinancialSnapshot.source == report.data_sources[0])
        .order_by(desc(m.FinancialSnapshot.fetched_at))
        .first()
    )


def _last_data_error(report: m.ResearchReport) -> str | None:
    session = object_session(report)
    if session is None or not report.data_sources:
        return None
    latest_log = (
        session.query(m.DataFetchLog)
        .filter(m.DataFetchLog.code == report.code, m.DataFetchLog.provider == report.data_sources[0], m.DataFetchLog.status == "FAILED")
        .order_by(desc(m.DataFetchLog.started_at))
        .first()
    )
    return latest_log.error_message if latest_log else None


def trend_payload(stock: m.Stock) -> list[dict]:
    rows = WarehouseMarketDataStore().get_daily_bars(stock.code, limit=7)
    if rows:
        return [{"date": row.trade_date.isoformat(), "price": round(row.close, 2)} for row in rows]
    return []


def watchlist_payload(item: m.WatchlistItem) -> dict:
    return {
        "id": item.id,
        "code": item.code,
        "symbol": item.stock.symbol,
        "name": item.stock.name,
        "source": item.source,
        "reportId": item.report_id,
        "note": item.note,
        "createdAt": dt_iso(item.created_at),
    }


def monitoring_payload(item: m.MonitoringItem, latest_signal=None, latest_risk=None, latest_order=None) -> dict:
    return {
        "id": item.id,
        "code": item.code,
        "symbol": item.stock.symbol,
        "name": item.stock.name,
        "enabled": item.enabled,
        "strategyId": item.strategy_id,
        "strategyName": item.strategy_name,
        "strategyParams": item.strategy_params,
        "riskParams": item.risk_params,
        "source": item.source,
        "reportId": item.report_id,
        "createdAt": dt_iso(item.created_at),
        "updatedAt": dt_iso(item.updated_at),
        "latestSignal": signal_payload(latest_signal) if latest_signal else None,
        "latestRiskCheck": risk_payload(latest_risk) if latest_risk else None,
        "latestOrder": order_payload(latest_order) if latest_order else None,
    }


def limit_up_break_snapshot_payload(snapshot: m.LimitUpBreakSnapshot, items: list[m.LimitUpBreakItem] | None = None) -> dict:
    if items is None:
        session = object_session(snapshot)
        items = []
        if session is not None:
            items = (
                session.query(m.LimitUpBreakItem)
                .filter(m.LimitUpBreakItem.snapshot_id == snapshot.id)
                .order_by(m.LimitUpBreakItem.previous_limit_up_height.desc(), m.LimitUpBreakItem.code.asc())
                .all()
            )
    return {
        "id": snapshot.id,
        "tradeDate": snapshot.trade_date.isoformat(),
        "previousTradeDate": snapshot.previous_trade_date.isoformat() if snapshot.previous_trade_date else None,
        "threshold": snapshot.threshold,
        "provider": snapshot.data_source,
        "priceAdjustment": snapshot.price_adjustment,
        "candidateCount": snapshot.candidate_count,
        "breakCount": snapshot.break_count,
        "suspendedBreakCount": snapshot.suspended_break_count,
        "generatedAt": dt_iso(snapshot.generated_at),
        "updatedAt": dt_iso(snapshot.updated_at),
        "items": [limit_up_break_item_payload(item) for item in items],
    }


def limit_up_break_item_payload(item: m.LimitUpBreakItem) -> dict:
    return {
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "previousLimitUpHeight": item.previous_limit_up_height,
        "changePercent": item.change_percent,
        "amount": item.amount,
        "intradayBreak": item.intraday_break,
        "breakType": item.break_type,
    }


def signal_payload(signal: m.Signal) -> dict:
    return {
        "id": signal.id,
        "runId": signal.run_id,
        "traceId": signal.trace_id,
        "code": signal.code,
        "type": signal.type,
        "reason": signal.reason,
        "confidence": signal.confidence,
        "generatedAt": dt_iso(signal.generated_at),
    }


def risk_payload(risk: m.RiskCheck) -> dict:
    return {
        "id": risk.id,
        "runId": risk.run_id,
        "traceId": risk.trace_id,
        "signalId": risk.signal_id,
        "time": dt_iso(risk.checked_at),
        "code": risk.code,
        "signal": risk.signal,
        "passed": risk.passed,
        "status": risk.status,
        "reason": risk.reason,
        "rule": risk.rule,
    }


def order_payload(order: m.PaperOrder) -> dict:
    return {
        "id": order.id,
        "runId": order.run_id,
        "traceId": order.trace_id,
        "signalId": order.signal_id,
        "riskCheckId": order.risk_check_id,
        "createTime": dt_iso(order.create_time),
        "code": order.code,
        "symbol": order.stock.symbol,
        "name": order.stock.name,
        "side": order.side,
        "type": order.side,
        "orderType": order.order_type,
        "quantity": order.quantity,
        "price": order.price,
        "rawPrice": order.raw_price,
        "executedPrice": order.executed_price,
        "slippageAmount": order.slippage_amount,
        "commission": order.commission,
        "stampTax": order.stamp_tax,
        "totalFee": order.total_fee,
        "estimatedAmount": order.estimated_amount,
        "finalAmount": order.final_amount,
        "netAmount": order.net_amount,
        "filledQuantity": order.filled_quantity,
        "avgPrice": order.avg_price,
        "status": order.status,
        "rejectReason": order.reject_reason,
    }


def position_payload(position: m.Position) -> dict:
    return {
        "id": position.id,
        "accountId": position.account_id,
        "code": position.code,
        "symbol": position.stock.symbol,
        "name": position.stock.name,
        "quantity": position.quantity,
        "available": position.available,
        "costPrice": position.cost_price,
        "currentPrice": position.current_price,
        "marketValue": position.market_value,
        "realizedPnl": position.realized_pnl,
        "unrealizedPnl": position.unrealized_pnl,
        "profitProgress": position.profit_progress,
        "lastRunId": position.last_run_id,
        "lastTraceId": position.last_trace_id,
        "updateTime": dt_iso(position.update_time),
    }


def log_payload(log: m.SystemLog) -> dict:
    return {
        "id": log.id,
        "time": dt_iso(log.time),
        "level": log.level,
        "module": log.module,
        "code": log.code,
        "event": log.event,
        "detail": log.detail,
        "relId": log.rel_id,
        "runId": log.run_id,
        "traceId": log.trace_id,
    }
