# 数据层

当前代码中有两条数据路径，它们共享 AkShare provider，但职责不同。

## 单股票刷新路径

入口：

- `POST /api/v1/data/stocks/{code}/refresh`
- `GET /api/v1/data/stocks/{code}/status`
- `GET /api/v1/data/fetch-logs`

代码：

- `backend/app/routers/data.py`
- `backend/app/services/data_service.py`
- `backend/app/providers/akshare_provider.py`

行为：

- 仅支持 `akshare` / `ak` provider。
- 股票代码支持 `600519`、`SH600519`、`600519.SH` 等格式。
- 刷新会拉取单只股票基础信息、日 K、财务摘要和交易日历。
- 日 K 会写入 `data/warehouse/daily_bars`。
- 股票基础信息、财务快照、fetch log 等业务状态写入 SQLite。
- AkShare 失败时会写入 `data_fetch_log`；如已有缓存，接口返回 stale cache。

## Warehouse 同步路径

入口：

- `python scripts/init_history_data.py`
- `python scripts/sync_daily_data.py`
- `python scripts/sync_today_if_trading_day.py`
- `python scripts/reconcile_daily_data.py`

代码：

- `backend/app/data_layer/providers/akshare.py`
- `backend/app/data_layer/sync/jobs.py`
- `backend/app/data_layer/warehouse/normalize.py`
- `backend/app/data_layer/quality/validators.py`
- `backend/app/data_layer/storage/*`

目录：

```text
data/
  raw/{provider}/...
  warehouse/
    daily_bars/
    index_daily_bars/
    instruments/
    trading_calendar/
  metadata/
    sync_state.db
    reports/
```

当前 warehouse 数据集：

- `instruments`
- `trading_calendar`
- `daily_bars`
- `index_daily_bars`

当前价格口径：

- 同步任务只写 `raw`。
- 断板监控和断板后走势只接受 `raw` / `none`。
- `qfq` / `hfq` 尚不是当前实现。

## 常用命令

```bash
python scripts/init_history_data.py \
  --provider akshare \
  --start-date 2020-01-01 \
  --limit 100 \
  --sleep 0.3

python scripts/sync_daily_data.py \
  --provider akshare \
  --lookback-days 20 \
  --board-filter main

python scripts/reconcile_daily_data.py \
  --provider akshare \
  --lookback-days 5 \
  --threshold 2
```

`reconcile_daily_data.py` 会先同步最近数据，再检查主板非 ST 覆盖率，最后生成最新连板断板快照。

## 测试依据

- `tests/test_beta_data_layer.py`
- `tests/test_data_layer_contracts.py`
- `tests/test_data_layer_sync_jobs.py`
- `tests/test_data_layer_storage.py`
- `tests/test_data_layer_normalize_quality.py`
- `tests/test_data_layer_cli.py`
