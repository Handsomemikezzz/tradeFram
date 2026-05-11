from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from ..providers.akshare import AkShareDataLayerProvider
from ..providers.base import DataLayerDailyBar, DataLayerIndexDailyBar, DataLayerInstrument, DataLayerProvider, DataLayerTradingDay
from ..quality.validators import validate_daily_bars, validate_index_daily_bars, validate_instruments, validate_trading_calendar
from ..storage.metadata_store import MetadataStore
from ..storage.parquet_store import ParquetStore
from ..storage.paths import DataLayerPaths
from ..warehouse.normalize import normalize_daily_bars, normalize_index_daily_bars, normalize_instruments, normalize_trading_calendar
from ..warehouse.schemas import CORE_INDEXES

PRICE_ADJUSTMENTS = ("raw",)


class SyncCircuitBreaker(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncOptions:
    data_root: Path = Path("data")
    provider_name: str = "akshare"
    start_date: date | None = None
    end_date: date | None = None
    lookback_days: int = 20
    limit: int | None = None
    codes: list[str] | None = None
    sleep: float = 0.0
    max_retries: int = 1
    retry_backoff: float = 1.0
    timeout: int = 30
    resume: bool = False
    resume_run_id: str | None = None
    retry_failed: bool = False
    dry_run: bool = False
    circuit_breaker_min_items: int = 30
    circuit_breaker_failure_rate: float = 0.8


@dataclass(frozen=True)
class SyncResult:
    run_id: str
    provider: str
    job_type: str
    status: str
    success_items: int
    failed_items: int
    skipped_items: int
    warning_count: int
    report_path: Path


def init_history_data(options: SyncOptions, *, provider: DataLayerProvider | None = None) -> SyncResult:
    provider = provider or _resolve_provider(options.provider_name)
    start_date = options.start_date or date(2020, 1, 1)
    end_date = options.end_date or date.today()
    return _run_sync("init_history_data", options, provider, start_date, end_date)


def sync_daily_data(options: SyncOptions, *, provider: DataLayerProvider | None = None) -> SyncResult:
    provider = provider or _resolve_provider(options.provider_name)
    end_date = options.end_date or date.today()
    calendar = provider.get_trading_calendar(end_date - timedelta(days=max(options.lookback_days * 3, 30)), end_date)
    open_days = [day.trade_date for day in calendar if day.is_open]
    sync_end_date = open_days[-1] if open_days else end_date
    start_date = open_days[-options.lookback_days] if len(open_days) >= options.lookback_days else (open_days[0] if open_days else end_date)
    return _run_sync("sync_daily_data", options, provider, start_date, sync_end_date, prefetched_calendar=calendar)


def _run_sync(
    job_type: str,
    options: SyncOptions,
    provider: DataLayerProvider,
    start_date: date,
    end_date: date,
    *,
    prefetched_calendar: list[DataLayerTradingDay] | None = None,
) -> SyncResult:
    paths = DataLayerPaths(Path(options.data_root))
    paths.ensure()
    metadata = MetadataStore(paths.sync_db)
    store = ParquetStore()
    run_id = metadata.create_run(provider=provider.name, job_type=job_type, start_date=start_date, end_date=end_date)
    resume_run_id = options.resume_run_id or run_id
    success_items = 0
    failed_items = 0
    skipped_items = 0
    warning_count = 0
    updated_at = datetime.now(UTC)

    try:
        instruments = provider.list_instruments()
        instruments_frame = normalize_instruments(instruments, source_provider=provider.name, source_updated_at=updated_at)
        warning_count += _write_dataset_item(metadata, store, paths, run_id, provider.name, "instruments", "all", instruments_frame, validate_instruments, options, start_date, end_date)
        success_items += 1

        calendar = prefetched_calendar or provider.get_trading_calendar(start_date, end_date)
        calendar_frame = normalize_trading_calendar(calendar, source_provider=provider.name, source_updated_at=updated_at)
        warning_count += _write_dataset_item(metadata, store, paths, run_id, provider.name, "trading_calendar", "all", calendar_frame, validate_trading_calendar, options, start_date, end_date)
        success_items += 1

        selected_instruments = _select_instruments(instruments, options)
        completed_daily = metadata.successful_item_keys(resume_run_id, dataset="daily_bars") if options.resume else set()
        daily_success_items = 0
        daily_failed_items = 0
        for instrument in selected_instruments:
            for price_adjustment in PRICE_ADJUSTMENTS:
                item_key = f"{instrument.code}:{price_adjustment}"
                if item_key in completed_daily:
                    skipped_items += 1
                    continue
                item_id = metadata.record_item(run_id=run_id, provider=provider.name, dataset="daily_bars", key=item_key, start_date=start_date, end_date=end_date)
                try:
                    bars = _with_retries(lambda price_adjustment=price_adjustment: provider.get_daily_bars(instrument.code, start_date, end_date, price_adjustment=price_adjustment), options)
                    frame = normalize_daily_bars(bars, source_provider=provider.name, source_updated_at=updated_at)
                    warning_count += _validate_or_raise(validate_daily_bars(frame))
                    if not options.dry_run:
                        _write_raw(store, paths, provider.name, "daily_bars", item_key, frame)
                        _merge_warehouse(store, paths.warehouse_root / "daily_bars", frame, ["code", "trade_date", "price_adjustment"], partition_cols=["code"])
                    metadata.mark_item_success(item_id, row_count=len(frame))
                    success_items += 1
                    daily_success_items += 1
                except Exception as exc:
                    metadata.mark_item_failed(item_id, error_message=str(exc))
                    failed_items += 1
                    daily_failed_items += 1
                _raise_if_circuit_breaker_tripped(daily_success_items, daily_failed_items, options)
                _sleep(options)

        completed_indexes = metadata.successful_item_keys(resume_run_id, dataset="index_daily_bars") if options.resume else set()
        for index_code in CORE_INDEXES:
            if index_code in completed_indexes:
                skipped_items += 1
                continue
            item_id = metadata.record_item(run_id=run_id, provider=provider.name, dataset="index_daily_bars", key=index_code, start_date=start_date, end_date=end_date)
            try:
                bars = _with_retries(lambda index_code=index_code: provider.get_index_daily_bars(index_code, start_date, end_date), options)
                frame = normalize_index_daily_bars(bars, source_provider=provider.name, source_updated_at=updated_at)
                warning_count += _validate_or_raise(validate_index_daily_bars(frame))
                if not options.dry_run:
                    _write_raw(store, paths, provider.name, "index_daily_bars", index_code, frame)
                    _merge_warehouse(store, paths.warehouse_root / "index_daily_bars", frame, ["index_code", "trade_date"], partition_cols=["index_code"])
                metadata.mark_item_success(item_id, row_count=len(frame))
                success_items += 1
            except Exception as exc:
                metadata.mark_item_failed(item_id, error_message=str(exc))
                failed_items += 1
            _sleep(options)

        status = "success" if failed_items == 0 else "partial"
        metadata.finish_run(run_id, status=status)
        report_path = _write_report(paths, run_id, provider.name, job_type, start_date, end_date, status, success_items, failed_items, skipped_items, warning_count)
        return SyncResult(run_id, provider.name, job_type, status, success_items, failed_items, skipped_items, warning_count, report_path)
    except Exception as exc:
        metadata.finish_run(run_id, status="failed", error_message=str(exc))
        report_path = _write_report(paths, run_id, provider.name, job_type, start_date, end_date, "failed", success_items, failed_items, skipped_items, warning_count, error_message=str(exc))
        return SyncResult(run_id, provider.name, job_type, "failed", success_items, failed_items + 1, skipped_items, warning_count, report_path)


def _write_dataset_item(
    metadata: MetadataStore,
    store: ParquetStore,
    paths: DataLayerPaths,
    run_id: str,
    provider_name: str,
    dataset: str,
    key: str,
    frame: pd.DataFrame,
    validator: Callable[[pd.DataFrame], object],
    options: SyncOptions,
    start_date: date,
    end_date: date,
) -> int:
    item_id = metadata.record_item(run_id=run_id, provider=provider_name, dataset=dataset, key=key, start_date=start_date, end_date=end_date)
    warning_count = _validate_or_raise(validator(frame))
    if not options.dry_run:
        _write_raw(store, paths, provider_name, dataset, key, frame)
        store.write_dataset(paths.warehouse_root / dataset, frame, overwrite=True)
    metadata.mark_item_success(item_id, row_count=len(frame))
    return warning_count


def _validate_or_raise(report) -> int:
    if report.has_errors:
        raise ValueError("; ".join(f"{issue.code}: {issue.message}" for issue in report.errors))
    return report.warning_count


def _write_raw(store: ParquetStore, paths: DataLayerPaths, provider_name: str, dataset: str, key: str, frame: pd.DataFrame) -> None:
    store.write_dataset(paths.raw_root / provider_name / dataset / f"key={key}", frame, overwrite=True)


def _merge_warehouse(store: ParquetStore, path: Path, frame: pd.DataFrame, keys: list[str], *, partition_cols: list[str] | None = None) -> None:
    if not frame.empty and partition_cols and len(partition_cols) == 1 and partition_cols[0] in frame.columns:
        partition_col = partition_cols[0]
        values = frame[partition_col].dropna().astype(str).unique()
        if len(values) == 1:
            partition_path = path / f"{partition_col}={values[0]}"
            if partition_path.exists():
                current = store.read_dataset(partition_path)
                if partition_col not in current.columns:
                    current[partition_col] = values[0]
                frame = pd.concat([current, frame], ignore_index=True)
            frame = frame.drop_duplicates(subset=keys, keep="last")
            store.write_dataset(partition_path, frame.drop(columns=[partition_col]), overwrite=True)
            return
    if path.exists():
        current = store.read_dataset(path)
        frame = pd.concat([current, frame], ignore_index=True)
    frame = frame.drop_duplicates(subset=keys, keep="last")
    store.write_dataset(path, frame, partition_cols=partition_cols, overwrite=True)


def _select_instruments(instruments: list[DataLayerInstrument], options: SyncOptions) -> list[DataLayerInstrument]:
    selected = instruments
    if options.codes:
        codes = {str(code).zfill(6) for code in options.codes}
        selected = [instrument for instrument in selected if instrument.code in codes]
    if options.limit is not None:
        selected = selected[: options.limit]
    return selected


def _with_retries(fn, options: SyncOptions):
    last_error: Exception | None = None
    attempts = max(options.max_retries, 1)
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(options.retry_backoff * (attempt + 1))
    raise last_error or RuntimeError("unknown sync error")


def _sleep(options: SyncOptions) -> None:
    if options.sleep > 0:
        time.sleep(options.sleep)


def _raise_if_circuit_breaker_tripped(success_items: int, failed_items: int, options: SyncOptions) -> None:
    total = success_items + failed_items
    if total < options.circuit_breaker_min_items:
        return
    if total == 0:
        return
    failure_rate = failed_items / total
    if failure_rate >= options.circuit_breaker_failure_rate:
        raise SyncCircuitBreaker(f"daily_bars failure rate {failure_rate:.0%} exceeded threshold after {total} items")


def _write_report(
    paths: DataLayerPaths,
    run_id: str,
    provider_name: str,
    job_type: str,
    start_date: date,
    end_date: date,
    status: str,
    success_items: int,
    failed_items: int,
    skipped_items: int,
    warning_count: int,
    *,
    error_message: str | None = None,
) -> Path:
    path = paths.reports_root / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "provider": provider_name,
        "job_type": job_type,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "status": status,
        "success_items": success_items,
        "failed_items": failed_items,
        "skipped_items": skipped_items,
        "warning_count": warning_count,
        "error_message": error_message,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _resolve_provider(provider_name: str) -> DataLayerProvider:
    if provider_name.strip().lower() in {"akshare", "ak"}:
        return AkShareDataLayerProvider()
    raise ValueError(f"unknown data layer provider: {provider_name}")
