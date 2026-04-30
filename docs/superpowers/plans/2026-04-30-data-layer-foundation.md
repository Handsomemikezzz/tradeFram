# Data Layer Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first-phase local data foundation: provider-neutral schemas, Parquet raw/warehouse storage, resumable sync metadata, CLI jobs, validation, and optional business-cache backfill.

**Architecture:** Add an isolated `backend/app/data_layer/` package so current business APIs keep using the existing SQLite path. CLI scripts parse arguments and call data-layer jobs. AkShare is one provider implementation; tests use fake providers and do not access the network.

**Tech Stack:** Python 3.12+, FastAPI app package conventions, SQLAlchemy business cache, SQLite metadata DB, pandas, pyarrow, duckdb, pytest.

---

### Task 1: Data-Layer Contracts And Schemas

**Files:**
- Create: `backend/app/data_layer/__init__.py`
- Create: `backend/app/data_layer/providers/__init__.py`
- Create: `backend/app/data_layer/providers/base.py`
- Create: `backend/app/data_layer/warehouse/__init__.py`
- Create: `backend/app/data_layer/warehouse/schemas.py`
- Create: `tests/test_data_layer_contracts.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write failing tests for provider contracts and schema columns**

Create `tests/test_data_layer_contracts.py` with tests that import `DataLayerProvider`, `DataLayerInstrument`, `DataLayerDailyBar`, `WAREHOUSE_SCHEMAS`, and `CORE_INDEXES`. Assert the provider protocol exposes methods for instruments, trading calendar, stock daily bars, and index daily bars. Assert warehouse schemas include the columns defined in the spec and `CORE_INDEXES` contains six symbols.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/test_data_layer_contracts.py -v`

Expected: FAIL because `backend.app.data_layer` does not exist.

- [ ] **Step 3: Implement dataclasses, protocol, schemas, and dependencies**

Add `pandas>=2.0.0`, `pyarrow>=15.0.0`, and `duckdb>=1.0.0` to `requirements.txt`. Implement frozen dataclasses in `providers/base.py`: `DataLayerInstrument`, `DataLayerTradingDay`, `DataLayerDailyBar`, `DataLayerIndexDailyBar`, `DataLayerAdjFactor`. Implement `DataLayerProvider` as an abstract base class with `list_instruments`, `get_trading_calendar`, `get_daily_bars`, and `get_index_daily_bars`. Implement `schemas.py` with `CORE_INDEXES` and `WAREHOUSE_SCHEMAS`.

- [ ] **Step 4: Verify task 1 passes**

Run: `pytest tests/test_data_layer_contracts.py -v`

Expected: PASS.

### Task 2: Paths, Parquet Store, Metadata Store

**Files:**
- Create: `backend/app/data_layer/storage/__init__.py`
- Create: `backend/app/data_layer/storage/paths.py`
- Create: `backend/app/data_layer/storage/parquet_store.py`
- Create: `backend/app/data_layer/storage/metadata_store.py`
- Create: `tests/test_data_layer_storage.py`

- [ ] **Step 1: Write failing tests for path creation, Parquet round-trip, and metadata state**

Create `tests/test_data_layer_storage.py`. Use `tmp_path` to assert `DataLayerPaths.ensure()` creates `raw`, `warehouse`, `metadata`, and `reports`. Assert `ParquetStore.write_dataset()` writes a DataFrame and `read_dataset()` can read it. Assert `MetadataStore` creates `sync_runs` and `sync_items`, records a run, records an item, marks it successful, and returns successful keys for resume.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/test_data_layer_storage.py -v`

Expected: FAIL because storage modules do not exist.

- [ ] **Step 3: Implement paths, Parquet helpers, and SQLite metadata**

Implement `DataLayerPaths` with `root`, `raw_root`, `warehouse_root`, `metadata_root`, `reports_root`, `sync_db`, and `ensure()`. Implement `ParquetStore.write_dataset(path, frame, partition_cols=None, overwrite=True)` and `read_dataset(path)`. Implement `MetadataStore` using `sqlite3`, schema creation, `create_run`, `finish_run`, `record_item`, `mark_item_success`, `mark_item_failed`, and `successful_item_keys`.

- [ ] **Step 4: Verify task 2 passes**

Run: `pytest tests/test_data_layer_storage.py -v`

Expected: PASS.

### Task 3: Normalization And Quality Validation

**Files:**
- Create: `backend/app/data_layer/warehouse/normalize.py`
- Create: `backend/app/data_layer/quality/__init__.py`
- Create: `backend/app/data_layer/quality/validators.py`
- Create: `tests/test_data_layer_normalize_quality.py`

- [ ] **Step 1: Write failing tests for normalization and validators**

Create `tests/test_data_layer_normalize_quality.py`. Build fake dataclass records and assert normalization returns pandas DataFrames with warehouse schema columns. Assert duplicate instruments and invalid OHLC data produce validation errors. Assert missing industry and suspicious daily counts produce warnings, not fatal errors.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/test_data_layer_normalize_quality.py -v`

Expected: FAIL because normalization and validators do not exist.

- [ ] **Step 3: Implement normalization and validation result objects**

Implement `normalize_instruments`, `normalize_trading_calendar`, `normalize_daily_bars`, and `normalize_index_daily_bars`. Implement `ValidationIssue`, `ValidationReport`, and validators for instruments, calendar, daily bars, and index bars. Keep validation deterministic and independent of AkShare.

- [ ] **Step 4: Verify task 3 passes**

Run: `pytest tests/test_data_layer_normalize_quality.py -v`

Expected: PASS.

### Task 4: AkShare Provider Adapter

**Files:**
- Create: `backend/app/data_layer/providers/akshare.py`
- Create: `tests/test_data_layer_akshare_provider.py`

- [ ] **Step 1: Write failing tests for AkShare adapter with monkeypatched fake module**

Create `tests/test_data_layer_akshare_provider.py`. Monkeypatch `backend.app.data_layer.providers.akshare._akshare` to return a fake object with AkShare-shaped methods. Assert the adapter converts stock lists, calendars, daily bars, and index daily bars to data-layer dataclasses.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/test_data_layer_akshare_provider.py -v`

Expected: FAIL because the adapter does not exist.

- [ ] **Step 3: Implement AkShareDataLayerProvider**

Implement `AkShareDataLayerProvider` using defensive column lookup. Use unadjusted daily bar requests. Keep failures as regular exceptions for sync jobs to classify. Do not import or change the existing business `AkShareMarketDataProvider`.

- [ ] **Step 4: Verify task 4 passes**

Run: `pytest tests/test_data_layer_akshare_provider.py -v`

Expected: PASS.

### Task 5: Sync Jobs, Reports, Resume, And Backfill

**Files:**
- Create: `backend/app/data_layer/sync/__init__.py`
- Create: `backend/app/data_layer/sync/jobs.py`
- Create: `backend/app/data_layer/sync/business_cache.py`
- Create: `tests/test_data_layer_sync_jobs.py`

- [ ] **Step 1: Write failing tests for limited init, daily sync, resume, reports, and optional backfill**

Create `tests/test_data_layer_sync_jobs.py`. Use a fake provider with two stocks and one index. Run `init_history_data(..., limit=1)` into `tmp_path` and assert raw files, warehouse files, metadata rows, and a JSON report exist. Run the same job with `resume=True` and assert already successful keys are skipped. Run `sync_daily_data(..., lookback_days=20)`. For backfill, use an isolated SQLite business DB if existing model imports allow it; otherwise test that the backfill function is only called when the option is true.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/test_data_layer_sync_jobs.py -v`

Expected: FAIL because sync jobs do not exist.

- [ ] **Step 3: Implement job options, provider resolution, sync orchestration, JSON reports, and optional backfill hook**

Implement `SyncOptions`, `SyncResult`, `init_history_data`, and `sync_daily_data`. Implement partial-success item handling, retry loop, sleep, `limit`, `codes`, `resume`, `retry_failed`, `dry_run`, and report writing. Implement `backfill_business_cache` as idempotent SQLAlchemy upserts for `Stock` and `PriceBar`.

- [ ] **Step 4: Verify task 5 passes**

Run: `pytest tests/test_data_layer_sync_jobs.py -v`

Expected: PASS.

### Task 6: CLI Entrypoints And End-To-End Verification

**Files:**
- Create: `scripts/init_history_data.py`
- Create: `scripts/sync_daily_data.py`
- Create: `tests/test_data_layer_cli.py`
- Modify: `README.md` or `docs/akshare-validation.md` only if a short usage note is needed.

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_data_layer_cli.py`. Call each script with `--help` using `subprocess.run` and assert exit code 0 plus expected flags. Test `--dry-run --limit 1 --data-root <tmp_path>` if the scripts support fake-provider injection through job-level tests rather than CLI.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/test_data_layer_cli.py -v`

Expected: FAIL because CLI scripts do not exist.

- [ ] **Step 3: Implement CLI scripts**

Implement argument parsing for all approved flags and call data-layer jobs. Include `--data-root`, `--provider`, `--start-date`, `--end-date`, `--lookback-days`, `--limit`, `--codes`, `--sleep`, `--max-retries`, `--retry-backoff`, `--timeout`, `--resume`, `--retry-failed`, `--dry-run`, and `--update-business-cache`.

- [ ] **Step 4: Run focused and regression tests**

Run:

```bash
pytest tests/test_data_layer_contracts.py tests/test_data_layer_storage.py tests/test_data_layer_normalize_quality.py tests/test_data_layer_akshare_provider.py tests/test_data_layer_sync_jobs.py tests/test_data_layer_cli.py -v
pytest tests/test_beta_data_layer.py tests/test_limit_up_break_monitor.py -v
```

Expected: PASS. Existing unrelated dirty files are not modified.

- [ ] **Step 5: Commit implementation**

Commit only data-layer files, tests, scripts, dependency changes, and optional short docs. Use Lore trailers and the required OmX co-author trailer.
