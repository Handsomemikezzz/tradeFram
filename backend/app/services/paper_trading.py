from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import PaperTradingRunCreate
from ..utils import api_error, new_id
from .data_service import get_recent_price_bars

TRACE_TEMPLATE = [
    {"step": "SIGNAL", "label": "Signal Engine", "status": "PENDING", "relId": None},
    {"step": "RISK_CHECK", "label": "Risk Engine", "status": "PENDING", "relId": None},
    {"step": "ORDER", "label": "Order Manager", "status": "PENDING", "relId": None},
    {"step": "EXECUTION", "label": "Paper Broker", "status": "PENDING", "relId": None},
    {"step": "POSITION", "label": "Position Manager", "status": "PENDING", "relId": None},
    {"step": "LOG", "label": "Trade Logger", "status": "PENDING", "relId": None},
]

DEFAULT_STRATEGY_PARAMS = {
    "maShortWindow": 5,
    "maLongWindow": 20,
    "minBarsRequired": 60,
    "orderQuantity": None,
}

DEFAULT_RISK_PARAMS = {
    "maxOrderValue": 50_000,
    "maxSingleStockPositionValue": 50_000,
    "maxTotalPositionRatio": 0.8,
    "maxDataStaleMinutes": 1440,
    "lotSize": 100,
    "commissionRate": 0.0003,
    "minCommission": 5.0,
    "stampTaxRate": 0.001,
    "slippageRate": 0.0005,
    "requireTradingTime": False,
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def trading_time_mode() -> dict:
    return {
        "allowManualRunOutsideTradingTime": _env_bool("ALLOW_MANUAL_RUN_OUTSIDE_TRADING_TIME", True),
        "strictTradingTimeCheck": _env_bool("STRICT_TRADING_TIME_CHECK", False),
    }


def get_engine_state(db: Session) -> m.PaperTradingEngineState:
    state = db.get(m.PaperTradingEngineState, "default")
    if state is None:
        state = m.PaperTradingEngineState(id="default", active=False, mode="PAPER_TRADING_ONLY")
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def set_engine_state(db: Session, active: bool, reason: str | None = None) -> m.PaperTradingEngineState:
    state = get_engine_state(db)
    state.active = active
    state.polling_enabled = active
    state.mode = "PAPER_TRADING_ONLY"
    state.updated_at = datetime.now(UTC)
    db.add(m.SystemLog(id=new_id("log"), level="INFO", module="PaperTrading", event="模拟交易系统开关", detail=reason or ("系统已启动" if active else "系统已停止")))
    db.commit()
    db.refresh(state)
    return state


def run_paper_trading(db: Session, payload: PaperTradingRunCreate) -> m.PaperTradingRun:
    if payload.dryRun:
        raise api_error(400, "DRY_RUN_NOT_SUPPORTED", "第一阶段暂不支持 dryRun；所有执行仍仅为 PAPER_TRADING_ONLY")

    run_id = new_id("run")
    run = m.PaperTradingRun(id=run_id, trigger=payload.trigger, status="RUNNING", summary={})
    db.add(run)
    db.flush()

    query = db.query(m.MonitoringItem)
    if payload.scope.enabledOnly:
        query = query.filter(m.MonitoringItem.enabled.is_(True))
    if payload.scope.monitoringItemIds:
        query = query.filter(m.MonitoringItem.id.in_(payload.scope.monitoringItemIds))
    items = query.all()

    summary = {
        "scannedStockCount": len(items),
        "generatedSignalCount": 0,
        "riskPassedCount": 0,
        "riskBlockedCount": 0,
        "createdPaperOrderCount": 0,
        "simulatedExecutionCount": 0,
        "durationMs": 0,
    }
    trace_ids: list[str] = []
    started = datetime.now(UTC)

    for item in items:
        trace = _create_trace(db, run_id, item)
        trace_ids.append(trace.id)
        stock = item.stock

        signal = _signal_engine(db, run_id, trace, item)
        summary["generatedSignalCount"] += 1

        risk = _risk_engine(db, run_id, trace, signal, stock)
        if risk.passed:
            summary["riskPassedCount"] += 1
        else:
            summary["riskBlockedCount"] += 1
            _mark_step(trace, "ORDER", "SKIPPED", None)
            _mark_step(trace, "EXECUTION", "SKIPPED", None)
            _mark_step(trace, "POSITION", "SKIPPED", None)
            _trade_logger(db, run_id, trace, stock.code, "WARN", "Trade Logger", f"{stock.name} 风控拦截，未创建模拟订单", risk.id)
            _finish_trace(trace, "COMPLETED")
            continue

        if signal.type == "HOLD":
            _mark_step(trace, "ORDER", "SKIPPED", None)
            _mark_step(trace, "EXECUTION", "SKIPPED", None)
            _mark_step(trace, "POSITION", "SKIPPED", None)
            _trade_logger(db, run_id, trace, stock.code, "INFO", "Trade Logger", f"{stock.name} 信号为 HOLD，未创建模拟订单", signal.id)
            _finish_trace(trace, "COMPLETED")
            continue

        order = _order_manager(db, run_id, trace, signal, risk, stock)
        summary["createdPaperOrderCount"] += 1
        execution = _paper_broker(db, run_id, trace, order)
        summary["simulatedExecutionCount"] += 1
        _position_manager(db, run_id, trace, order, execution, stock)
        _trade_logger(db, run_id, trace, stock.code, "SUCCESS", "Trade Logger", f"{stock.name} 模拟交易闭环完成", execution.id)
        _finish_trace(trace, "COMPLETED")

    run.status = "COMPLETED"
    run.finished_at = datetime.now(UTC)
    summary["durationMs"] = int((run.finished_at - started).total_seconds() * 1000)
    run.summary = {**summary, "traceIds": trace_ids}
    state = get_engine_state(db)
    state.last_run_id = run.id
    state.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)
    return run


def _create_trace(db: Session, run_id: str, item: m.MonitoringItem) -> m.ExecutionTrace:
    trace = m.ExecutionTrace(id=new_id("trace"), run_id=run_id, monitoring_item_id=item.id, code=item.code, current_step="SIGNAL", steps=[step.copy() for step in TRACE_TEMPLATE])
    db.add(trace)
    db.flush()
    return trace


def _mark_step(trace: m.ExecutionTrace, step: str, status: str, rel_id: str | None) -> None:
    steps = [s.copy() for s in trace.steps]
    for s in steps:
        if s["step"] == step:
            s["status"] = status
            s["relId"] = rel_id
    trace.steps = steps
    trace.current_step = step
    trace.updated_at = datetime.now(UTC)


def _finish_trace(trace: m.ExecutionTrace, status: str) -> None:
    trace.status = status
    trace.updated_at = datetime.now(UTC)


def _log(db: Session, *, run_id: str, trace_id: str, level: str, module: str, code: str | None, event: str, detail: str, rel_id: str | None = None) -> m.SystemLog:
    log = m.SystemLog(id=new_id("log"), level=level, module=module, code=code, event=event, detail=detail, rel_id=rel_id, run_id=run_id, trace_id=trace_id)
    db.add(log)
    db.flush()
    return log


def _signal_engine(db: Session, run_id: str, trace: m.ExecutionTrace, item: m.MonitoringItem) -> m.Signal:
    stock = item.stock
    signal_type, reason, confidence = generate_ma_signal(db, stock, strategy_params=item.strategy_params)
    signal = m.Signal(id=new_id("sig"), run_id=run_id, trace_id=trace.id, monitoring_item_id=item.id, code=stock.code, type=signal_type, reason=reason, confidence=confidence)
    db.add(signal)
    db.flush()
    _mark_step(trace, "SIGNAL", "COMPLETED", signal.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="INFO", module="SignalEngine", code=stock.code, event="Signal Engine", detail=reason, rel_id=signal.id)
    return signal


def generate_ma_signal(db: Session | None, stock: m.Stock | None, *, bars: list | None = None, strategy_params: dict | None = None) -> tuple[str, str, float]:
    """Generate v0.1 Beta MA5/MA20 paper-trading signal from recent daily bars."""
    params = _merge(DEFAULT_STRATEGY_PARAMS, strategy_params)
    if params.get("forceSignal") in {"BUY", "SELL", "HOLD"}:
        signal_type = str(params["forceSignal"])
        return signal_type, f"测试/配置强制信号：{signal_type}", 0.5
    if bars is None:
        if db is None or stock is None:
            return "HOLD", "日线数据不足：缺少数据库上下文或股票信息，策略保持观望", 0.0
        bars = get_recent_price_bars(db, stock.code, 60)

    short_window = int(params["maShortWindow"])
    long_window = int(params["maLongWindow"])
    min_bars = int(params["minBarsRequired"])
    required = max(short_window, long_window, min_bars)
    if len(bars) < required:
        return "HOLD", f"日线数据不足：仅 {len(bars)} 条，少于策略所需 {required} 条，策略保持观望", 0.0

    closes = [float(bar.close) for bar in bars[-60:]]
    ma5 = sum(closes[-short_window:]) / short_window
    ma20 = sum(closes[-long_window:]) / long_window
    if ma5 > ma20 * 1.01:
        return "BUY", f"MA 策略触发 BUY：最近60日数据中 MA5={ma5:.2f} 高于 MA20={ma20:.2f} 超过 1%，短期趋势走强", 0.76
    if ma5 < ma20 * 0.99:
        return "SELL", f"MA 策略触发 SELL：最近60日数据中 MA5={ma5:.2f} 低于 MA20={ma20:.2f} 超过 1%，短期趋势走弱", 0.72
    return "HOLD", f"MA 策略保持 HOLD：最近60日数据中 MA5={ma5:.2f} 与 MA20={ma20:.2f} 未形成明确偏离", 0.58


def _intended_quantity(signal: m.Signal, strategy_params: dict | None = None) -> int:
    params = _merge(DEFAULT_STRATEGY_PARAMS, strategy_params)
    if params.get("orderQuantity") is not None:
        return int(params["orderQuantity"])
    if signal.code == "000858":
        return 1000
    if signal.type in {"BUY", "SELL"}:
        return 100
    return 0


def _risk_engine(db: Session, run_id: str, trace: m.ExecutionTrace, signal: m.Signal, stock: m.Stock) -> m.RiskCheck:
    item = db.get(m.MonitoringItem, signal.monitoring_item_id)
    strategy_params = item.strategy_params if item else {}
    risk_params = _merge(DEFAULT_RISK_PARAMS, item.risk_params if item else {})
    quantity = _intended_quantity(signal, strategy_params)
    account = _get_account(db)
    position = _get_position(db, account.id, stock.code)
    latest_bar = _latest_price_bar(db, stock.code)

    if latest_bar is None:
        passed = False
        status = "BLOCKED"
        rule = "DATA_UNAVAILABLE"
        reason = "无可用日线行情数据，禁止创建模拟订单或模拟成交"
    elif _is_data_stale(latest_bar, risk_params):
        passed = False
        status = "BLOCKED"
        rule = "DATA_STALE"
        reason = f"行情缓存超过 {risk_params['maxDataStaleMinutes']} 分钟未刷新，禁止模拟成交"
    elif signal.confidence == 0.0 and "日线数据不足" in signal.reason:
        passed = False
        status = "BLOCKED"
        rule = "DATA_UNAVAILABLE"
        reason = signal.reason
    elif signal.type == "HOLD":
        passed = True
        status = "PASSED"
        rule = "BASIC_CHECK"
        reason = "HOLD 信号无需创建订单，基础检查通过"
    elif quantity <= 0:
        passed = False
        status = "BLOCKED"
        rule = "ORDER_QUANTITY"
        reason = "模拟订单数量必须大于 0"
    elif quantity % int(risk_params["lotSize"]) != 0:
        passed = False
        status = "BLOCKED"
        rule = "A_SHARE_LOT_SIZE"
        reason = f"A 股模拟买卖数量必须为 {risk_params['lotSize']} 股整数倍，当前 {quantity} 股"
    elif signal.type == "SELL":
        if position is None or position.available < quantity:
            passed = False
            status = "BLOCKED"
            rule = "SELL_POSITION_AVAILABLE"
            available = position.available if position else 0
            reason = f"SELL 信号需要可用持仓 {quantity} 股，但当前可用 {available} 股；T+1 未解锁持仓不可卖出"
        else:
            passed = True
            status = "PASSED"
            rule = "BASIC_CHECK"
            reason = "卖出信号具备足够可用模拟持仓，满足 A 股 T+1 可卖限制"
    else:
        amount = quantity * stock.price
        estimated_cost = amount + _fees("BUY", amount, risk_params)
        current_position_value = position.market_value if position else 0
        total_position_value = sum(p.market_value for p in db.query(m.Position).all())
        total_assets = account.cash + total_position_value
        projected_position_ratio = (total_position_value + amount) / total_assets if total_assets else 1
        time_mode = trading_time_mode()
        require_time = bool(risk_params.get("requireTradingTime")) or bool(time_mode["strictTradingTimeCheck"])
        if require_time and not _is_trading_time(db) and (time_mode["strictTradingTimeCheck"] or not time_mode["allowManualRunOutsideTradingTime"]):
            passed = False
            status = "BLOCKED"
            rule = "TRADING_TIME"
            reason = "严格交易时间模式开启，且当前不在可模拟成交交易时间内，默认不成交"
        elif amount > float(risk_params["maxOrderValue"]):
            passed = False
            status = "BLOCKED"
            rule = "MAX_ORDER_VALUE"
            reason = f"订单金额 {amount:,.2f} RMB 超过单笔上限 {float(risk_params['maxOrderValue']):,.2f} RMB"
        elif current_position_value + amount > float(risk_params["maxSingleStockPositionValue"]):
            passed = False
            status = "BLOCKED"
            rule = "MAX_SINGLE_STOCK_POS"
            reason = f"买入后单股持仓 {current_position_value + amount:,.2f} RMB 超过上限 {float(risk_params['maxSingleStockPositionValue']):,.2f} RMB"
        elif estimated_cost > account.cash:
            passed = False
            status = "BLOCKED"
            rule = "CASH_AVAILABLE"
            reason = f"可用现金不足：预计需 {estimated_cost:,.2f} RMB，当前现金 {account.cash:,.2f} RMB"
        elif projected_position_ratio > float(risk_params["maxTotalPositionRatio"]):
            passed = False
            status = "BLOCKED"
            rule = "MAX_TOTAL_POSITION_RATIO"
            reason = f"买入后总仓位比例 {projected_position_ratio:.2%} 超过上限 {float(risk_params['maxTotalPositionRatio']):.2%}"
        else:
            passed = True
            status = "PASSED"
            rule = "BASIC_CHECK"
            reason = "符合 A 股模拟交易风控规则：百股整数、现金、持仓比例、行情数据均通过"
    risk = m.RiskCheck(id=new_id("risk"), run_id=run_id, trace_id=trace.id, signal_id=signal.id, code=stock.code, signal=signal.type, status=status, passed=passed, reason=reason, rule=rule)
    db.add(risk)
    db.flush()
    _mark_step(trace, "RISK_CHECK", "COMPLETED", risk.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="INFO" if passed else "WARN", module="RiskEngine", code=stock.code, event="Risk Engine", detail=reason, rel_id=risk.id)
    return risk


def _order_manager(db: Session, run_id: str, trace: m.ExecutionTrace, signal: m.Signal, risk: m.RiskCheck, stock: m.Stock) -> m.PaperOrder:
    if not risk.passed:
        raise api_error(409, "RISK_CHECK_FAILED", "风控未通过，不允许创建模拟订单")
    item = db.get(m.MonitoringItem, signal.monitoring_item_id)
    strategy_params = item.strategy_params if item else {}
    order = m.PaperOrder(
        id=new_id("ORD"),
        run_id=run_id,
        trace_id=trace.id,
        signal_id=signal.id,
        risk_check_id=risk.id,
        code=stock.code,
        side=signal.type,
        order_type="LIMIT",
        quantity=_intended_quantity(signal, strategy_params),
        price=stock.price,
        raw_price=stock.price,
        estimated_amount=round(stock.price * _intended_quantity(signal, strategy_params), 2),
        status="PENDING",
    )
    db.add(order)
    db.flush()
    _mark_step(trace, "ORDER", "COMPLETED", order.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="INFO", module="OrderManager", code=stock.code, event="Order Manager", detail=f"创建模拟订单 {order.id}", rel_id=order.id)
    return order


def _paper_broker(db: Session, run_id: str, trace: m.ExecutionTrace, order: m.PaperOrder) -> m.PaperExecution:
    signal = db.get(m.Signal, order.signal_id)
    item = db.get(m.MonitoringItem, signal.monitoring_item_id) if signal else None
    risk_params = _merge(DEFAULT_RISK_PARAMS, item.risk_params if item else {})
    slippage = float(risk_params["slippageRate"])
    fill_price = round(order.price * (1 + slippage), 4) if order.side == "BUY" else round(order.price * (1 - slippage), 4)
    estimated_amount = round(order.price * order.quantity, 2)
    final_amount = round(fill_price * order.quantity, 2)
    slippage_amount = round(abs(final_amount - estimated_amount), 2)
    commission, stamp_tax, total_fee = _fee_breakdown(order.side, final_amount, risk_params)
    net_amount = round(final_amount + total_fee, 2) if order.side == "BUY" else round(final_amount - total_fee, 2)
    order.status = "FILLED"
    order.filled_quantity = order.quantity
    order.avg_price = fill_price
    order.executed_price = fill_price
    order.slippage_amount = slippage_amount
    order.commission = commission
    order.stamp_tax = stamp_tax
    order.total_fee = total_fee
    order.estimated_amount = estimated_amount
    order.final_amount = final_amount
    order.net_amount = net_amount
    execution = m.PaperExecution(
        id=new_id("exec"),
        run_id=run_id,
        trace_id=trace.id,
        order_id=order.id,
        code=order.code,
        filled_quantity=order.quantity,
        avg_price=fill_price,
        raw_price=order.price,
        executed_price=fill_price,
        slippage_amount=slippage_amount,
        commission=commission,
        stamp_tax=stamp_tax,
        total_fee=total_fee,
        estimated_amount=estimated_amount,
        final_amount=final_amount,
        net_amount=net_amount,
        status="FILLED",
    )
    db.add(execution)
    db.flush()
    _mark_step(trace, "EXECUTION", "COMPLETED", execution.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="SUCCESS", module="PaperBroker", code=order.code, event="Paper Broker", detail=f"订单 {order.id} 已按 {fill_price:.2f} 模拟成交 {order.quantity} 股；滑点 {slippage_amount:.2f}，佣金 {commission:.2f}，印花税 {stamp_tax:.2f}，费用合计 {total_fee:.2f}，净额 {net_amount:.2f}", rel_id=execution.id)
    return execution


def _position_manager(db: Session, run_id: str, trace: m.ExecutionTrace, order: m.PaperOrder, execution: m.PaperExecution, stock: m.Stock) -> m.Position:
    account = _get_account(db)
    position_id = f"pos_{account.id}_{stock.code}"
    position = db.get(m.Position, position_id)
    if position is None:
        position = m.Position(id=position_id, account_id=account.id, code=stock.code, quantity=0, available=0, cost_price=0, current_price=stock.price)
        db.add(position)
        db.flush()

    if order.side == "BUY":
        gross = execution.final_amount
        fee = execution.total_fee
        total_cost_before = position.cost_price * position.quantity
        total_cost_after = total_cost_before + gross + fee
        position.quantity += execution.filled_quantity
        # A 股 T+1：当日买入数量不进入 available，下一交易日才可卖。
        position.cost_price = round(total_cost_after / position.quantity, 4)
        account.cash -= gross + fee
    elif order.side == "SELL":
        gross = execution.final_amount
        fee = execution.total_fee
        position.quantity -= execution.filled_quantity
        position.available -= execution.filled_quantity
        account.cash += gross - fee
        position.realized_pnl += round((execution.avg_price - position.cost_price) * execution.filled_quantity - fee, 2)

    position.current_price = stock.price
    position.market_value = round(position.quantity * stock.price, 2)
    position.unrealized_pnl = round((stock.price - position.cost_price) * position.quantity, 2)
    invested = position.cost_price * position.quantity
    position.profit_progress = round((position.unrealized_pnl / invested) * 100, 2) if invested else 0
    position.last_run_id = run_id
    position.last_trace_id = trace.id
    position.update_time = datetime.now(UTC)
    account.updated_at = datetime.now(UTC)
    db.flush()
    _mark_step(trace, "POSITION", "COMPLETED", position.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="SUCCESS", module="PositionManager", code=stock.code, event="Position Manager", detail=f"持仓已更新：{stock.name} {position.quantity} 股", rel_id=position.id)
    return position


def _trade_logger(db: Session, run_id: str, trace: m.ExecutionTrace, code: str, level: str, event: str, detail: str, rel_id: str | None) -> None:
    _mark_step(trace, "LOG", "COMPLETED", rel_id)
    _log(db, run_id=run_id, trace_id=trace.id, level=level, module="TradeLogger", code=code, event=event, detail=detail, rel_id=rel_id)


def _merge(defaults: dict, overrides: dict | None) -> dict:
    return {**defaults, **(overrides or {})}


def _get_account(db: Session) -> m.PaperAccount:
    account = db.get(m.PaperAccount, "paper_default")
    if account is None:
        account = m.PaperAccount(id="paper_default", initial_cash=1_000_000, cash=1_000_000)
        db.add(account)
        db.flush()
    return account


def _get_position(db: Session, account_id: str, code: str) -> m.Position | None:
    return db.get(m.Position, f"pos_{account_id}_{code}")


def _latest_price_bar(db: Session, code: str) -> m.PriceBar | None:
    return db.query(m.PriceBar).filter(m.PriceBar.code == code).order_by(desc(m.PriceBar.trade_date)).first()


def _is_data_stale(bar: m.PriceBar, risk_params: dict) -> bool:
    fetched_at = bar.fetched_at if bar.fetched_at.tzinfo else bar.fetched_at.replace(tzinfo=UTC)
    return datetime.now(UTC) - fetched_at > timedelta(minutes=int(risk_params["maxDataStaleMinutes"]))


def _is_trading_time(db: Session) -> bool:
    today = datetime.now(UTC).date()
    day = db.query(m.TradingCalendar).filter(m.TradingCalendar.trade_date == today, m.TradingCalendar.is_open.is_(True)).first()
    return day is not None


def _fees(side: str, amount: float, risk_params: dict) -> float:
    return _fee_breakdown(side, amount, risk_params)[2]


def _fee_breakdown(side: str, amount: float, risk_params: dict) -> tuple[float, float, float]:
    commission = max(amount * float(risk_params["commissionRate"]), float(risk_params["minCommission"]))
    stamp_tax = amount * float(risk_params["stampTaxRate"]) if side == "SELL" else 0.0
    commission = round(commission, 2)
    stamp_tax = round(stamp_tax, 2)
    return commission, stamp_tax, round(commission + stamp_tax, 2)


def _risk_params_for_order(db: Session, order: m.PaperOrder) -> dict:
    signal = db.get(m.Signal, order.signal_id)
    item = db.get(m.MonitoringItem, signal.monitoring_item_id) if signal else None
    return _merge(DEFAULT_RISK_PARAMS, item.risk_params if item else {})
