from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.database import SessionLocal
from backend.app.serializers import limit_up_break_snapshot_payload
from backend.app.services.limit_up_breaks import generate_limit_up_break_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or overwrite a limit-up break snapshot.")
    parser.add_argument("--date", dest="trade_date", help="Trade date in YYYY-MM-DD format. Defaults to latest local price bar date.")
    parser.add_argument("--threshold", type=int, default=2, help="Minimum previous limit-up streak height.")
    parser.add_argument("--provider", default="AkShare", help="Price bar data source.")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.trade_date) if args.trade_date else None
    with SessionLocal() as db:
        snapshot = generate_limit_up_break_snapshot(db, target_date, threshold=args.threshold, provider=args.provider)
        db.commit()
        db.refresh(snapshot)
        payload = limit_up_break_snapshot_payload(snapshot)
        print(
            f"{payload['tradeDate']} provider={payload['provider']} threshold={payload['threshold']} "
            f"candidates={payload['candidateCount']} breaks={payload['breakCount']} suspended={payload['suspendedBreakCount']}"
        )


if __name__ == "__main__":
    main()
