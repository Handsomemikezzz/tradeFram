from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.data_layer.providers.akshare import AkShareDataLayerProvider
from backend.app.data_layer.sync.jobs import SyncOptions, sync_daily_data
from backend.app.data_layer.warehouse.reader import WarehouseMarketDataStore
from backend.app.services.screeners import (
    SCAN_LOOKBACK_TRADE_DAYS,
    _load_regulatory_indexes,
    _uptrend_bars_by_code,
    main_board_non_st_stocks,
)
from backend.app.services.uptrend import MIN_LISTING_BARS, regulatory_index_for_stock
from scripts.sync_cli import add_price_adjustment_args, parse_price_adjustments


def _uptrend_eligible_count(store: WarehouseMarketDataStore, target_date: date) -> tuple[int, int, dict[str, int]]:
    trade_dates = store.trade_dates(end_date=target_date, price_adjustment="raw")
    if target_date not in trade_dates:
        target_date = trade_dates[-1] if trade_dates else target_date
    target_index = trade_dates.index(target_date)
    start_date = trade_dates[max(0, target_index - SCAN_LOOKBACK_TRADE_DAYS)]

    stocks = main_board_non_st_stocks(store=store)
    codes = {stock.code for stock in stocks}
    raw_frame = store.daily_bars_frame(
        codes=codes,
        start_date=start_date,
        end_date=target_date,
        price_adjustment="raw",
    )
    qfq_frame = store.daily_bars_frame(
        codes=codes,
        start_date=start_date,
        end_date=target_date,
        price_adjustment="qfq",
    )
    raw_by = _uptrend_bars_by_code(raw_frame, with_change_percent=True)
    qfq_by = _uptrend_bars_by_code(qfq_frame, with_change_percent=False)
    index_by = _load_regulatory_indexes(store, start_date, target_date)

    eligible = 0
    reasons = {"no_raw": 0, "no_qfq": 0, "no_index": 0}
    for stock in stocks:
        index_code, _ = regulatory_index_for_stock(stock.code)
        raw_bars = raw_by.get(stock.code, [])
        qfq_bars = qfq_by.get(stock.code, [])
        index_bars = index_by.get(index_code, [])
        if len(raw_bars) < MIN_LISTING_BARS:
            reasons["no_raw"] += 1
            continue
        if len(qfq_bars) < MIN_LISTING_BARS:
            reasons["no_qfq"] += 1
            continue
        if len(index_bars) < 31:
            reasons["no_index"] += 1
            continue
        eligible += 1
    return len(stocks), eligible, reasons


def _print_coverage(label: str, store: WarehouseMarketDataStore, target_date: date) -> int:
    total, eligible, reasons = _uptrend_eligible_count(store, target_date)
    trade_dates = store.trade_dates(end_date=target_date, price_adjustment="raw")
    if target_date in trade_dates:
        start_date = trade_dates[max(0, trade_dates.index(target_date) - SCAN_LOOKBACK_TRADE_DAYS)]
    else:
        start_date = trade_dates[max(0, len(trade_dates) - SCAN_LOOKBACK_TRADE_DAYS)] if trade_dates else target_date
    index_by = _load_regulatory_indexes(store, start_date, target_date)
    print(f"[{label}] trade_date={target_date.isoformat()} eligible={eligible}/{total}")
    print(f"  blocked: no_raw={reasons['no_raw']} no_qfq={reasons['no_qfq']} no_index={reasons['no_index']}")
    for code, bars in index_by.items():
        print(f"  index {code}: {len(bars)} bars")
    return eligible


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill raw+qfq daily bars and regulatory indexes required by the uptrend screener.",
    )
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--provider", default="akshare")
    parser.add_argument("--lookback-days", type=int, default=120, help="Trading days to resync (>= 90 recommended).")
    parser.add_argument("--board-filter", choices=["all", "main"], default="main")
    parser.add_argument("--end-date", help="YYYY-MM-DD or today. Default: today.")
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--retry-backoff", type=float, default=3.0)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--resume-run-id")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true", help="Skip sync and only print uptrend data coverage.")
    add_price_adjustment_args(parser)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    os.environ["DATA_ROOT"] = str(data_root)
    store = WarehouseMarketDataStore(data_root)
    end_date = date.today() if not args.end_date or args.end_date == "today" else date.fromisoformat(args.end_date)
    trade_dates = store.trade_dates(end_date=end_date, price_adjustment="raw")
    target_date = end_date if end_date in trade_dates else (trade_dates[-1] if trade_dates else end_date)

    before = _print_coverage("before", store, target_date)
    if args.verify_only:
        return 0 if before > 0 else 1

    if args.provider.strip().lower() not in {"akshare", "ak"}:
        print("error: backfill_uptrend_data currently supports provider=akshare only", file=sys.stderr)
        return 2

    provider = AkShareDataLayerProvider()
    result = sync_daily_data(
        SyncOptions(
            data_root=data_root,
            provider_name=args.provider,
            end_date=end_date,
            lookback_days=args.lookback_days,
            board_filter=None if args.board_filter == "all" else args.board_filter,
            price_adjustments=parse_price_adjustments(args.price_adjustment),
            sleep=args.sleep,
            max_retries=args.max_retries,
            retry_backoff=args.retry_backoff,
            timeout=args.timeout,
            resume=args.resume,
            resume_run_id=args.resume_run_id,
            retry_failed=args.retry_failed,
            dry_run=args.dry_run,
            circuit_breaker_min_items=5000,
            circuit_breaker_failure_rate=1.0,
        ),
        provider=provider,
    )
    print(
        f"sync status={result.status} run_id={result.run_id} "
        f"success={result.success_items} failed={result.failed_items} report={result.report_path}"
    )
    if result.status == "failed":
        return 1

    after = _print_coverage("after", store, target_date)
    if after == 0:
        print("warning: still 0 eligible stocks — check AkShare network/proxy and re-run with --resume if partial.")
        return 1

    print("next: open Screeners -> 上行趋势 -> 生成快照")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
