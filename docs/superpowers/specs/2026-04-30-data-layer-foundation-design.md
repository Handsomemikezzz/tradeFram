# Data Layer Foundation Design

## Purpose

The current system has an AkShare-only, single-stock data path that supports stock research, paper trading, and limit-up break monitoring through SQLite business tables. That path is useful for v0.1 behavior, but it is not enough for stable research, reproducible backtests, full-market scans, or future provider replacement.

This design adds a modular data foundation without rewriting existing business features. The first implementation will build a local raw and warehouse data store, a resumable sync pipeline, and explicit optional backfill into the existing business cache.

## Scope

The first phase covers:

- Stock instruments.
- Trading calendar.
- A-share unadjusted daily bars.
- Core index unadjusted daily bars.
- Adjustment-factor schema and interface reservation, without requiring real adjustment-factor sync.

The default historical window is `2020-01-01` through the requested end date, normally today.

Out of scope for this phase:

- Rewriting research, paper trading, or limit-up break APIs to read from the warehouse by default.
- Real QMT integration.
- Tushare, Wind, Choice, or iFinD integration.
- Full financial statements, index constituent history, ST history, suspension history, and limit-price status datasets.
- Intraday bars and live market data.

## Approach

Use a modular data-layer pipeline under `backend/app/data_layer/`. CLI scripts remain thin entry points and call reusable jobs. AkShare is the first provider implementation. QMT and other sources can later implement the same provider boundary.

The system writes provider-shaped data into `data/raw/<provider>/...` and normalized internal data into `data/warehouse/...`. Raw data preserves traceability when AkShare changes fields or returns incomplete data. Warehouse data provides stable Parquet schemas for DuckDB, research, backtests, and future business readers.

## Module Layout

```text
backend/app/data_layer/
  __init__.py
  providers/
    __init__.py
    base.py
    akshare.py
  storage/
    __init__.py
    paths.py
    parquet_store.py
    metadata_store.py
  sync/
    __init__.py
    jobs.py
    tasks.py
  quality/
    __init__.py
    validators.py
  warehouse/
    __init__.py
    schemas.py
    normalize.py

scripts/init_history_data.py
scripts/sync_daily_data.py
```

Existing `backend/app/providers/` and `backend/app/services/data_service.py` stay in place for the current business flow. The new data layer is additive in phase one.

## Data Layout

```text
data/
  raw/
    akshare/
      instruments/
      trading_calendar/
      daily_bars/
      index_daily_bars/
    qmt/
  warehouse/
    instruments/
    trading_calendar/
    daily_bars/
    index_daily_bars/
    adj_factors/
  metadata/
    sync_state.db
    reports/
```

The `qmt` raw directory is reserved. It does not imply QMT is implemented in this phase.

## Warehouse Schemas

`warehouse/instruments/instruments.parquet`:

```text
code
symbol
exchange
name
market
industry
list_date
delist_date
status
source_provider
source_updated_at
```

`warehouse/trading_calendar/calendar.parquet`:

```text
trade_date
exchange
is_open
source_provider
source_updated_at
```

`warehouse/daily_bars/year=<YYYY>/part.parquet`:

```text
code
symbol
exchange
trade_date
open
high
low
close
volume
amount
price_adjustment
source_provider
source_updated_at
```

`price_adjustment` is `none` in phase one.

`warehouse/index_daily_bars/year=<YYYY>/part.parquet`:

```text
index_code
symbol
name
trade_date
open
high
low
close
volume
amount
source_provider
source_updated_at
```

Initial core indexes:

```text
000001.SH
399001.SZ
399006.SZ
000300.SH
000905.SH
000852.SH
```

`warehouse/adj_factors/` reserved schema:

```text
code
symbol
trade_date
adj_factor
source_provider
source_updated_at
```

## Raw Data Rules

Raw data is provider-specific and keeps source-shaped fields. The data layer may add minimal metadata:

```text
provider
dataset
fetched_at
request_params
payload_version
```

Example paths:

```text
data/raw/akshare/daily_bars/year=2026/code=600519/part.parquet
data/raw/akshare/instruments/fetched_date=2026-04-30/part.parquet
```

Raw data is not a stable consumer contract. Warehouse data is the stable contract.

## CLI Entry Points

History initialization:

```bash
python scripts/init_history_data.py \
  --provider akshare \
  --start-date 2020-01-01 \
  --end-date today \
  --sleep 0.3 \
  --resume
```

Daily sync:

```bash
python scripts/sync_daily_data.py \
  --provider akshare \
  --lookback-days 20 \
  --sleep 0.3 \
  --resume
```

Supported controls:

```text
--limit
--codes
--sleep
--max-retries
--retry-backoff
--timeout
--resume
--retry-failed
--dry-run
--update-business-cache
```

`--update-business-cache` is explicit. By default, the data warehouse does not modify existing SQLite business tables.

## Sync Flow

`init_history_data`:

1. Create `data/`, warehouse directories, and metadata DB when missing.
2. Fetch instruments to raw, normalize to warehouse.
3. Fetch trading calendar to raw, normalize to warehouse.
4. Read instruments and fetch daily bars for each stock from `2020-01-01` to end date.
5. Write each successful item to raw and warehouse, then update sync item state.
6. Fetch core index daily bars.
7. Run quality validation.
8. Write a JSON report under `data/metadata/reports/`.
9. If requested, backfill existing SQLite business cache.

`sync_daily_data`:

1. Refresh instruments.
2. Determine the recent trading-day lookback window, defaulting to 20 trading days.
3. Fetch and overwrite daily bar partitions for the affected years.
4. Fetch and overwrite index daily bar partitions for the affected years.
5. Run quality validation.
6. Write sync state and report.
7. Optionally backfill the business cache.

## Resume And Retry

`data/metadata/sync_state.db` tracks runs and items.

`sync_runs`:

```text
id
provider
job_type
start_date
end_date
status
started_at
finished_at
error_message
```

`sync_items`:

```text
id
run_id
provider
dataset
key
start_date
end_date
status
row_count
error_message
attempt_count
updated_at
```

With `--resume`, successful items are skipped. Failed items rerun only when `--retry-failed` is set. Stale `running` items may be treated as recoverable failures.

The pipeline allows partial success. A failed stock or index is an item failure, not a whole-run failure, unless the storage layer or provider initialization fails.

## Quality Validation

Instrument checks:

- `code` is six digits.
- `symbol` follows the internal format, for example `600519.SH`.
- `exchange` is `SH`, `SZ`, or `BJ`.
- `name` is present.
- `code` is unique.

Trading-calendar checks:

- `trade_date` is unique.
- `is_open` is boolean.
- The requested date range has at least one open trading day.

Daily-bar checks:

- `code + trade_date + price_adjustment` is unique.
- OHLC fields are present.
- `high >= low`.
- `high >= open` and `high >= close`.
- `low <= open` and `low <= close`.
- `volume >= 0`.
- `amount >= 0`.
- Abnormal per-day stock-count drops produce warnings.

Index-bar checks:

- `index_code + trade_date` is unique.
- Core indexes are not all missing.
- OHLC, volume, and amount checks match daily bars.

Error categories:

- `fatal`: metadata DB creation failure, warehouse write failure, provider initialization failure.
- `item_failed`: one stock or index fails to fetch or normalize.
- `warning`: incomplete but usable data, such as missing industry or suspicious daily counts.

## Business Cache Backfill

Phase one keeps the current business flow intact. Existing APIs continue reading from current SQLite tables unless explicitly changed later.

When `--update-business-cache` is passed, the sync job may backfill:

- `Stock` from `warehouse/instruments`.
- `PriceBar` from `warehouse/daily_bars`.

The backfill must be idempotent and should not delete unrelated business rows. It should use the same normalized code and unadjusted price semantics as the current business layer.

## Testing Strategy

Default tests use a fake provider and do not access the network.

Test coverage should include:

- Provider protocol behavior with fake data.
- Raw path and warehouse path generation.
- Parquet write, overwrite, and partition behavior.
- Raw-to-warehouse normalization.
- Metadata run and item state transitions.
- Resume behavior.
- Quality validation success, warning, and failure paths.
- CLI dry-run and limited sync flows.
- Optional business-cache backfill.

Real AkShare verification stays as a smoke path and is not required for default CI.

## Acceptance Criteria

- A clean workspace can initialize `data/`, `data/warehouse/`, and `data/metadata/sync_state.db`.
- `init_history_data` can run with `--limit 5` and produce raw and warehouse Parquet files.
- The default historical range starts at `2020-01-01`.
- `sync_daily_data` can sync a recent 20-trading-day window.
- Failed items are recorded and can be resumed or retried.
- DuckDB can query warehouse Parquet files.
- Quality reports are written under `data/metadata/reports/`.
- Existing business APIs and tests keep working without `--update-business-cache`.
- With `--update-business-cache`, current `Stock` and `PriceBar` cache tables can be explicitly refreshed from warehouse data.

## Future Extension

QMT should enter as a new provider implementation, not as direct calls inside research, strategy, backtest, or trading modules. Its raw data can keep QMT-specific fields under `data/raw/qmt/`, while normalized records must satisfy the same warehouse schemas.

Later phases can add:

- Real adjustment factors.
- Financial datasets.
- Index constituents.
- Industry and concept classification.
- ST, suspension, and limit-price status.
- Provider cross-checking.
- Warehouse-first readers for backtests, limit-up break monitoring, and research.
