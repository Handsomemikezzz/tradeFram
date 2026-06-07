from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.database import SessionLocal
from backend.app.data_layer.providers.akshare import AkShareDataLayerProvider
from backend.app.data_layer.sync.jobs import SyncOptions, sync_daily_data
from backend.app.data_layer.warehouse.reader import WarehouseInstrument, WarehouseMarketDataStore
from backend.app.services.limit_up_breaks import MIN_TARGET_COVERAGE, generate_limit_up_break_snapshot
from backend.app.utils import CN_TZ


@dataclass(frozen=True)
class CoverageResult:
    target_date: date
    available_bars: int
    expected_bars: int
    coverage: float
    min_coverage: float


def resolve_target_trade_date(data_root: Path, *, now: datetime | None = None):
    current = now or datetime.now(CN_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=CN_TZ)
    current = current.astimezone(CN_TZ)
    open_dates = WarehouseMarketDataStore(data_root).open_trade_dates(end_date=current.date())
    return open_dates[-1] if open_dates else None


def calculate_main_board_coverage(data_root: Path, target_date) -> CoverageResult:
    store = WarehouseMarketDataStore(data_root)
    stocks = _main_board_non_st_stocks(store.list_instruments())
    stock_codes = {stock.code for stock in stocks}
    counts = store.daily_bar_counts_by_date(codes=stock_codes if stock_codes else None, end_date=target_date)
    expected = len(stocks)
    available = counts.get(target_date, 0)
    coverage = available / expected if expected else 0
    return CoverageResult(
        target_date=target_date,
        available_bars=available,
        expected_bars=expected,
        coverage=round(coverage, 4),
        min_coverage=MIN_TARGET_COVERAGE,
    )


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    os.environ["DATA_ROOT"] = str(data_root)
    now = _parse_now(args.now)

    if args.provider.strip().lower() not in {"akshare", "ak"}:
        print("error unsupported provider: reconcile_daily_data currently supports provider=akshare only", file=sys.stderr)
        return 2

    provider = AkShareDataLayerProvider()
    current = now or datetime.now(CN_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=CN_TZ)
    sync_end_date = current.astimezone(CN_TZ).date()
    sync_result = sync_daily_data(
        SyncOptions(
            data_root=data_root,
            provider_name=args.provider,
            end_date=sync_end_date,
            lookback_days=args.lookback_days,
            board_filter=None if args.board_filter == "all" else args.board_filter,
            price_adjustments=tuple(args.price_adjustment or ["raw"]),
            sleep=args.sleep,
            max_retries=args.max_retries,
            retry_backoff=args.retry_backoff,
            timeout=args.timeout,
            circuit_breaker_min_items=args.circuit_breaker_min_items,
            circuit_breaker_failure_rate=args.circuit_breaker_failure_rate,
        ),
        provider=provider,
    )
    print(
        f"sync status={sync_result.status} run_id={sync_result.run_id} "
        f"success={sync_result.success_items} failed={sync_result.failed_items} report={sync_result.report_path}"
    )
    if sync_result.status == "failed":
        return 1

    target_date = resolve_target_trade_date(data_root, now=now)
    if target_date is None:
        print("incomplete target_date=None reason=no_open_trade_date")
        return 1

    coverage = calculate_main_board_coverage(data_root, target_date)
    if coverage.expected_bars == 0 or coverage.coverage < coverage.min_coverage:
        print(
            f"incomplete target_date={target_date.isoformat()} "
            f"available={coverage.available_bars} expected={coverage.expected_bars} "
            f"coverage={coverage.coverage:.4f} min_coverage={coverage.min_coverage:.4f}"
        )
        return 1

    with SessionLocal() as db:
        snapshot = generate_limit_up_break_snapshot(db, target_date, threshold=args.threshold, provider=_snapshot_provider(args.provider))
        db.commit()
        db.refresh(snapshot)
        print(
            f"ready target_date={snapshot.trade_date.isoformat()} snapshot_id={snapshot.id} "
            f"candidates={snapshot.candidate_count} breaks={snapshot.break_count} suspended={snapshot.suspended_break_count}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resync recent market data, verify coverage, and generate the latest limit-up break snapshot.")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--provider", default="akshare")
    parser.add_argument("--lookback-days", type=int, default=5)
    parser.add_argument("--board-filter", choices=["all", "main"], default="main")
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--retry-backoff", type=float, default=3.0)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--circuit-breaker-min-items", type=int, default=5000)
    parser.add_argument("--circuit-breaker-failure-rate", type=float, default=1.0)
    parser.add_argument("--threshold", type=int, default=2)
    parser.add_argument("--now", help="Override current CN time for tests, ISO-8601 format.")
    parser.add_argument(
        "--price-adjustment",
        action="append",
        choices=["raw", "qfq", "hfq"],
        default=None,
        dest="price_adjustment",
        help="Daily bar price adjustment to sync. Repeat to sync multiple. Default: raw.",
    )
    return parser


def _parse_now(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=CN_TZ)
    return parsed.astimezone(CN_TZ)


def _snapshot_provider(provider: str) -> str:
    return "AkShare" if provider.strip().lower() in {"akshare", "ak"} else provider


def _main_board_non_st_stocks(stocks: list[WarehouseInstrument]) -> list[WarehouseInstrument]:
    return [stock for stock in stocks if stock.status.lower() == "active" and _is_main_board(stock) and not _is_st(stock)]


def _is_main_board(stock: WarehouseInstrument) -> bool:
    if stock.exchange == "SH":
        return stock.code.startswith(("600", "601", "603", "605"))
    if stock.exchange == "SZ":
        return stock.code.startswith(("000", "001", "002", "003"))
    return False


def _is_st(stock: WarehouseInstrument) -> bool:
    normalized = stock.name.upper().replace(" ", "")
    return normalized.startswith(("*ST", "ST", "S*ST"))


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
