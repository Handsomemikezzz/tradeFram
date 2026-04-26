#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal
from backend.app.seed import init_db
from backend.app.services.data_service import DataFetchError, fetch_log_payload, get_provider, refresh_stock_data
from backend.app.services.paper_trading import generate_ma_signal
from backend.app import models as m


DEFAULT_CODES = ["600519", "000858", "300750", "601318"]


def main() -> int:
    provider_name = sys.argv[1] if len(sys.argv) > 1 else os.getenv("MARKET_DATA_PROVIDER", "akshare")
    codes = sys.argv[2:] or DEFAULT_CODES
    init_db()
    results = []
    with SessionLocal() as db:
        provider = get_provider(provider_name)
        for code in codes:
            try:
                dataset = refresh_stock_data(db, code, provider.name)
                db.commit()
                stock = dataset["stock"]
                bars = dataset["bars"]
                closes = [float(bar.close) for bar in bars[-20:]]
                ma5 = round(sum(closes[-5:]) / 5, 2) if len(closes) >= 5 else None
                ma20 = round(sum(closes[-20:]) / 20, 2) if len(closes) >= 20 else None
                signal, reason, confidence = generate_ma_signal(db, stock, bars=bars)
                latest_log = (
                    db.query(m.DataFetchLog)
                    .filter(m.DataFetchLog.code == stock.code, m.DataFetchLog.provider == provider.name)
                    .order_by(m.DataFetchLog.started_at.desc())
                    .first()
                )
                results.append(
                    {
                        "code": stock.code,
                        "name": stock.name,
                        "provider": provider.name,
                        "priceBarCount": len(bars),
                        "latestTradeDate": bars[-1].trade_date.isoformat() if bars else None,
                        "ma5": ma5,
                        "ma20": ma20,
                        "signal": signal,
                        "signalReason": reason,
                        "signalConfidence": confidence,
                        "dataCompleteness": dataset["dataCompleteness"],
                        "fetchLogStatus": latest_log.status if latest_log else None,
                        "fetchLog": fetch_log_payload(latest_log) if latest_log else None,
                    }
                )
            except DataFetchError as exc:
                db.rollback()
                results.append({"code": code, "provider": provider.name, "status": "FAILED", "errorCode": exc.code, "error": exc.message})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
