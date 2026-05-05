from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.data_layer.providers.akshare import AkShareDataLayerProvider
from backend.app.data_layer.sync.jobs import SyncOptions, sync_daily_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync recent market data if today is a trading day.")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--provider", default="akshare")
    parser.add_argument("--lookback-days", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-backoff", type=float, default=2.0)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--resume-run-id")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.provider.strip().lower() not in {"akshare", "ak"}:
        raise ValueError("sync_today_if_trading_day currently supports provider=akshare only")

    today = date.today()
    provider = AkShareDataLayerProvider()
    calendar = provider.get_trading_calendar(today - timedelta(days=7), today)
    today_row = next((day for day in calendar if day.trade_date == today), None)
    if not today_row or not today_row.is_open:
        print(f"skipped: {today.isoformat()} is not an open trading day")
        return 0

    result = sync_daily_data(
        SyncOptions(
            data_root=Path(args.data_root),
            provider_name=args.provider,
            end_date=today,
            lookback_days=args.lookback_days,
            sleep=args.sleep,
            max_retries=args.max_retries,
            retry_backoff=args.retry_backoff,
            timeout=args.timeout,
            resume=args.resume,
            resume_run_id=args.resume_run_id,
            retry_failed=args.retry_failed,
            dry_run=args.dry_run,
        ),
        provider=provider,
    )
    print(f"{result.status} run_id={result.run_id} success={result.success_items} failed={result.failed_items} report={result.report_path}")
    return 0 if result.status in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
