import argparse
import json
import time
from datetime import datetime, timezone

import requests


def check_health(base_url: str):
    r = requests.get(f"{base_url}/health", timeout=15)
    payload = r.json()
    ok = r.status_code == 200 and payload.get("status") in {"healthy", "degraded"}
    return {
        "name": "health_endpoint",
        "ok": ok,
        "status_code": r.status_code,
        "payload": payload,
    }


def check_telegram_status(base_url: str):
    r = requests.get(f"{base_url}/api/telegram/status", timeout=20)
    payload = r.json()
    cfg = payload.get("config", {})
    return {
        "name": "telegram_config",
        "ok": r.status_code == 200 and cfg.get("core_credentials_present", False),
        "status_code": r.status_code,
        "payload": {
            "available": payload.get("available"),
            "core_credentials_present": cfg.get("core_credentials_present"),
            "missing_core": cfg.get("missing_core"),
        },
    }


def check_query(base_url: str, query: str, max_latency_sec: float):
    started = time.time()
    r = requests.post(
        f"{base_url}/api/search",
        json={"query": query, "location": "Kenya", "include_telegram": False},
        timeout=240,
    )
    latency = time.time() - started
    payload = r.json()
    status = payload.get("status")
    count = int(payload.get("count", 0) or 0)
    ok = (
        r.status_code == 200
        and status in {"success", "no_results"}
        and latency <= max_latency_sec
    )
    return {
        "name": f"query:{query}",
        "ok": ok,
        "status_code": r.status_code,
        "latency_sec": round(latency, 3),
        "count": count,
        "status": status,
        "message": payload.get("message"),
        "top_lead": (payload.get("leads") or [None])[0],
    }


def run_gate(base_url: str, queries, max_latency_sec: float):
    checks = []
    checks.append(check_health(base_url))
    checks.append(check_telegram_status(base_url))
    for q in queries:
        checks.append(check_query(base_url, q, max_latency_sec))

    summary = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c["ok"]),
        "failed": sum(1 for c in checks if not c["ok"]),
        "checks": checks,
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary["failed"] == 0 else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delta 9 production gate checker.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--queries", nargs="+", default=["water tank", "pipes", "shoes"])
    parser.add_argument("--max-latency-sec", type=float, default=70.0)
    args = parser.parse_args()
    raise SystemExit(run_gate(args.base_url, args.queries, args.max_latency_sec))
