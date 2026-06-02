#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal
from backend.app.services.pattern_a import PATTERN_A_STRATEGY_TYPE
from backend.app.services.screeners import ScreenerError, generate_pattern_a_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate screener snapshot")
    parser.add_argument("--strategy", default=PATTERN_A_STRATEGY_TYPE, choices=[PATTERN_A_STRATEGY_TYPE])
    parser.add_argument("--trade-date", dest="trade_date", default=None)
    parser.add_argument("--provider", default="AkShare")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    trade_date = date.fromisoformat(args.trade_date) if args.trade_date else None
    with SessionLocal() as db:
        try:
            snapshot = generate_pattern_a_snapshot(db, trade_date, provider=args.provider)
            db.commit()
            print(
                f"Generated {args.strategy} snapshot {snapshot.id} for {snapshot.trade_date.isoformat()} "
                f"(confirmed={snapshot.confirmed_count}, pending={snapshot.pending_count})"
            )
        except ScreenerError as exc:
            print(f"[ERROR] {exc.code}: {exc.message}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
