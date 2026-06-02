# 连板断板监控

连板断板监控基于本地 warehouse 未复权日 K，生成主板非 ST 股票的收盘断板快照。

## 代码入口

- Router: `backend/app/routers/limit_up_breaks.py`
- Service: `backend/app/services/limit_up_breaks.py`
- CLI: `scripts/run_limit_up_break_snapshot.py`
- 前端页面：`src/pages/LimitUpBreakMonitor.tsx`
- API client: `src/services/api/limitUpBreakApi.ts`

## API

- `POST /api/v1/limit-up-breaks/snapshots`
- `GET /api/v1/limit-up-breaks/snapshots/default/latest`
- `GET /api/v1/limit-up-breaks/snapshots/{trade_date}`
- `GET /api/v1/limit-up-breaks/stocks/{code}/post-break-bars`

所有业务 API 挂在 `/api/v1` 下。字段细节以 FastAPI OpenAPI 为准。

## 快照规则

- 股票范围：沪深主板。
- 排除：ST、非 active 股票。
- 价格口径：未复权日 K，内部使用 `raw`，响应中展示为 `none`。
- 默认连板门槛：上一交易日已达到 `2` 连板。
- 涨停价：上一交易日收盘价乘以 `1.10`，按 `0.01` 四舍五入。
- 断板定义：当日收盘未涨停。
- 停牌处理：候选股当日无 bar 时记为 `SUSPENDED`。
- 覆盖率保护：主板非 ST 当日行情覆盖率低于 `0.995` 时返回 `DATA_COVERAGE_TOO_LOW`。
- 同一 `trade_date + threshold + provider` 重跑会覆盖原快照 items。

默认快照日期：

- 若今天是交易日且中国时间未到 18:00，默认读取上一开市日。
- 若今天是交易日且已到 18:00，默认读取今天。
- 周末或非交易日默认读取最近开市日。

## 断板后走势

`GET /api/v1/limit-up-breaks/stocks/{code}/post-break-bars`：

- 参数：`breakDate`、`maxForwardDays`、`adjustment`
- `maxForwardDays` 默认 5，允许 0 到 20。
- `adjustment` 只支持 `none` / `raw`。
- 返回 T0 起最多 `maxForwardDays + 1` 个交易日。
- 缺失或停牌日不会补假数据。
- `changePercent` 按前一条可用 bar 计算；T0 使用断板日前一交易日作为基准。

## CLI

```bash
python scripts/run_limit_up_break_snapshot.py \
  --date 2026-04-30 \
  --threshold 2 \
  --provider AkShare
```

省略 `--date` 时，service 会按默认快照日期解析。

## 测试依据

- `tests/test_limit_up_break_monitor.py`
- `tests/test_reconcile_daily_data.py`
