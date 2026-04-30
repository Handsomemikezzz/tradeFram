from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.data_layer.sync.jobs import SyncOptions, init_history_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize local historical market data warehouse.")
    _add_common_args(parser)
    parser.add_argument("--start-date", default="2020-01-01", help="History start date, YYYY-MM-DD.")
    args = parser.parse_args()
    result = init_history_data(
        SyncOptions(
            data_root=Path(args.data_root),
            provider_name=args.provider,
            start_date=_parse_date(args.start_date),
            end_date=_parse_date(args.end_date) if args.end_date else date.today(),
            limit=args.limit,
            codes=_parse_codes(args.codes),
            sleep=args.sleep,
            max_retries=args.max_retries,
            retry_backoff=args.retry_backoff,
            timeout=args.timeout,
            resume=args.resume,
            resume_run_id=args.resume_run_id,
            retry_failed=args.retry_failed,
            dry_run=args.dry_run,
            update_business_cache=args.update_business_cache,
        )
    )
    print(f"{result.status} run_id={result.run_id} success={result.success_items} failed={result.failed_items} report={result.report_path}")
    return 0 if result.status in {"success", "partial"} else 1


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--provider", default="akshare")
    parser.add_argument("--end-date")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--codes")
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-backoff", type=float, default=2.0)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--resume-run-id")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--update-business-cache", action="store_true")


def _parse_codes(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_date(raw: str) -> date:
    if raw == "today":
        return date.today()
    return date.fromisoformat(raw)


if __name__ == "__main__":
    raise SystemExit(main())
