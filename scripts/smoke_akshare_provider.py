#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


BASE_URL = "http://127.0.0.1:8000/api/v1"


def request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        data = json.loads(exc.read().decode("utf-8"))
        raise RuntimeError(f"{method} {path} failed: {exc.code} {json.dumps(data, ensure_ascii=False)}") from exc
    if not data.get("success"):
        raise RuntimeError(f"{method} {path} returned error envelope: {json.dumps(data, ensure_ascii=False)}")
    print(f"OK   {method} {path}")
    return data["data"]


def main() -> int:
    code = sys.argv[1] if len(sys.argv) > 1 else "600519"
    encoded_code = urllib.parse.quote(code, safe="")
    refresh = request("POST", f"/data/stocks/{encoded_code}/refresh?provider=akshare")
    status = request("GET", f"/data/stocks/{encoded_code}/status?provider=akshare")
    task = request("POST", "/research/tasks", {"code": code, "options": {"provider": "akshare"}})
    report = request("GET", f"/research/reports/by-code/{task['code']}")
    logs = request("GET", f"/data/fetch-logs?code={urllib.parse.quote(task['code'])}&provider=AkShare&pageSize=5")
    print(
        json.dumps(
            {
                "refresh": refresh,
                "status": status,
                "taskId": task["taskId"],
                "reportDataMeta": report["dataMeta"],
                "recentFetchLogs": logs["items"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
