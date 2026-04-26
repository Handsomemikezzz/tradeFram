#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any


BASE_URL = "http://127.0.0.1:8000/api/v1"


def request(method: str, path: str, payload: dict[str, Any] | None = None, *, accept_duplicate: bool = False) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        data = json.loads(exc.read().decode("utf-8"))
        code = data.get("error", {}).get("code")
        if accept_duplicate and code in {"WATCHLIST_ALREADY_EXISTS", "MONITORING_ITEM_ALREADY_EXISTS"}:
            print(f"SKIP {method} {path}: {code}")
            return data
        raise RuntimeError(f"{method} {path} failed: {exc.code} {data}") from exc

    if not data.get("success"):
        raise RuntimeError(f"{method} {path} returned error envelope: {data}")
    print(f"OK   {method} {path}")
    return data["data"]


def main() -> int:
    code = sys.argv[1] if len(sys.argv) > 1 else "300750"
    request("GET", "/system/status")
    request("GET", "/data-sources/health")
    task = request("POST", "/research/tasks", {"code": code})
    request("GET", f"/research/tasks/{task['taskId']}")
    request("GET", f"/research/reports/by-code/{code}")
    request("POST", "/watchlist/items", {"code": code, "source": "SMOKE"}, accept_duplicate=True)
    request("POST", "/monitoring-pool/items", {"code": code, "enabled": True, "source": "SMOKE"}, accept_duplicate=True)
    run = request("POST", "/paper-trading/runs", {"trigger": "MANUAL", "scope": {"enabledOnly": True}})
    request("GET", "/orders")
    request("GET", "/portfolio/positions")
    request("GET", "/risk-checks")
    request("GET", "/logs")
    print(json.dumps({"taskId": task["taskId"], "runId": run["runId"], "summary": run["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
