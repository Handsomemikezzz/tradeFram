from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import PaperTradingRunCreate
from ..utils import api_error, new_id

TRACE_TEMPLATE = [
    {"step": "SIGNAL", "label": "Signal Engine", "status": "PENDING", "relId": None},
    {"step": "RISK_CHECK", "label": "Risk Engine", "status": "PENDING", "relId": None},
    {"step": "ORDER", "label": "Order Manager", "status": "PENDING", "relId": None},
    {"step": "EXECUTION", "label": "Paper Broker", "status": "PENDING", "relId": None},
    {"step": "POSITION", "label": "Position Manager", "status": "PENDING", "relId": None},
    {"step": "LOG", "label": "Trade Logger", "status": "PENDING", "relId": None},
]


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
    if stock.code == "300750":
        signal_type = "BUY"
        reason = "mock 策略：放量突破20日均线，生成买入信号"
        confidence = 0.78
    elif stock.code == "000858":
        signal_type = "BUY"
        reason = "mock 策略：低位反弹，但将触发单股限额风控"
        confidence = 0.66
    else:
        signal_type = "HOLD"
        reason = "mock 策略：价格处于中位线，无明显趋势"
        confidence = 0.61
    signal = m.Signal(id=new_id("sig"), run_id=run_id, trace_id=trace.id, monitoring_item_id=item.id, code=stock.code, type=signal_type, reason=reason, confidence=confidence)
    db.add(signal)
    db.flush()
    _mark_step(trace, "SIGNAL", "COMPLETED", signal.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="INFO", module="SignalEngine", code=stock.code, event="Signal Engine", detail=reason, rel_id=signal.id)
    return signal


def _intended_quantity(signal: m.Signal) -> int:
    if signal.code == "000858":
        return 1000
    if signal.code == "300750":
        return 100
    return 0


def _risk_engine(db: Session, run_id: str, trace: m.ExecutionTrace, signal: m.Signal, stock: m.Stock) -> m.RiskCheck:
    if signal.type == "HOLD":
        passed = True
        status = "PASSED"
        rule = "BASIC_CHECK"
        reason = "HOLD 信号无需创建订单，基础检查通过"
    else:
        quantity = _intended_quantity(signal)
        amount = quantity * stock.price
        if amount > 50_000:
            passed = False
            status = "BLOCKED"
            rule = "MAX_SINGLE_STOCK_POS"
            reason = f"订单金额 {amount:,.2f} RMB 超过最大单股持仓限制 50,000 RMB"
        else:
            passed = True
            status = "PASSED"
            rule = "BASIC_CHECK"
            reason = "各项指标符合第一阶段 mock 风控规则"
    risk = m.RiskCheck(id=new_id("risk"), run_id=run_id, trace_id=trace.id, signal_id=signal.id, code=stock.code, signal=signal.type, status=status, passed=passed, reason=reason, rule=rule)
    db.add(risk)
    db.flush()
    _mark_step(trace, "RISK_CHECK", "COMPLETED", risk.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="INFO" if passed else "WARN", module="RiskEngine", code=stock.code, event="Risk Engine", detail=reason, rel_id=risk.id)
    return risk


def _order_manager(db: Session, run_id: str, trace: m.ExecutionTrace, signal: m.Signal, risk: m.RiskCheck, stock: m.Stock) -> m.PaperOrder:
    if not risk.passed:
        raise api_error(409, "RISK_CHECK_FAILED", "风控未通过，不允许创建模拟订单")
    order = m.PaperOrder(
        id=new_id("ORD"),
        run_id=run_id,
        trace_id=trace.id,
        signal_id=signal.id,
        risk_check_id=risk.id,
        code=stock.code,
        side=signal.type,
        order_type="LIMIT",
        quantity=_intended_quantity(signal),
        price=stock.price,
        status="PENDING",
    )
    db.add(order)
    db.flush()
    _mark_step(trace, "ORDER", "COMPLETED", order.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="INFO", module="OrderManager", code=stock.code, event="Order Manager", detail=f"创建模拟订单 {order.id}", rel_id=order.id)
    return order


def _paper_broker(db: Session, run_id: str, trace: m.ExecutionTrace, order: m.PaperOrder) -> m.PaperExecution:
    order.status = "FILLED"
    order.filled_quantity = order.quantity
    order.avg_price = order.price
    execution = m.PaperExecution(id=new_id("exec"), run_id=run_id, trace_id=trace.id, order_id=order.id, code=order.code, filled_quantity=order.quantity, avg_price=order.price, status="FILLED")
    db.add(execution)
    db.flush()
    _mark_step(trace, "EXECUTION", "COMPLETED", execution.id)
    _log(db, run_id=run_id, trace_id=trace.id, level="SUCCESS", module="PaperBroker", code=order.code, event="Paper Broker", detail=f"订单 {order.id} 已按 {order.price:.2f} 模拟成交 {order.quantity} 股", rel_id=execution.id)
    return execution


def _position_manager(db: Session, run_id: str, trace: m.ExecutionTrace, order: m.PaperOrder, execution: m.PaperExecution, stock: m.Stock) -> m.Position:
    account = db.get(m.PaperAccount, "paper_default")
    if account is None:
        account = m.PaperAccount(id="paper_default", initial_cash=1_000_000, cash=1_000_000)
        db.add(account)
        db.flush()
    position_id = f"pos_{account.id}_{stock.code}"
    position = db.get(m.Position, position_id)
    if position is None:
        position = m.Position(id=position_id, account_id=account.id, code=stock.code, quantity=0, available=0, cost_price=0, current_price=stock.price)
        db.add(position)
        db.flush()

    if order.side == "BUY":
        total_cost_before = position.cost_price * position.quantity
        total_cost_after = total_cost_before + execution.avg_price * execution.filled_quantity
        position.quantity += execution.filled_quantity
        position.available += execution.filled_quantity
        position.cost_price = round(total_cost_after / position.quantity, 4)
        account.cash -= execution.avg_price * execution.filled_quantity
    elif order.side == "SELL":
        position.quantity -= execution.filled_quantity
        position.available -= execution.filled_quantity
        account.cash += execution.avg_price * execution.filled_quantity

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
