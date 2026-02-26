import argparse
import json
import statistics
import time
from datetime import datetime, timezone

import requests


def run_soak(base_url: str, queries, loops: int, interval_sec: int, min_count_alert: int):
    results = []
    for i in range(1, loops + 1):
        for q in queries:
            started = time.time()
            rec = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "loop": i,
                "query": q,
                "ok": False,
                "status_code": None,
                "status": None,
                "count": 0,
                "latency_sec": None,
                "error": None,
                "alert": None,
            }
            try:
                r = requests.post(
                    f"{base_url}/api/search",
                    json={"query": q, "location": "Kenya"},
                    timeout=120,
                )
                rec["status_code"] = r.status_code
                payload = r.json()
                rec["status"] = payload.get("status")
                rec["count"] = int(payload.get("count", 0) or 0)
                rec["ok"] = r.status_code == 200 and rec["status"] in {"success", "no_results"}
                if rec["count"] < min_count_alert:
                    rec["alert"] = f"low_lead_count<{min_count_alert}"
            except Exception as e:
                rec["error"] = str(e)
                rec["alert"] = "request_failed"
            rec["latency_sec"] = round(time.time() - started, 3)
            print(json.dumps(rec))
            results.append(rec)
        if i < loops:
            time.sleep(interval_sec)

    latencies = [r["latency_sec"] for r in results if isinstance(r["latency_sec"], (int, float))]
    counts = [r["count"] for r in results]
    alerts = [r for r in results if r.get("alert")]
    summary = {
        "runs": len(results),
        "ok_runs": sum(1 for r in results if r["ok"]),
        "avg_latency_sec": round(statistics.mean(latencies), 3) if latencies else None,
        "p95_latency_sec": round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 3) if latencies else None,
        "avg_count": round(statistics.mean(counts), 2) if counts else 0.0,
        "alerts": len(alerts),
    }
    print("=== SOAK SUMMARY ===")
    print(json.dumps(summary, indent=2))
    if alerts:
        print("=== ALERTS ===")
        for a in alerts:
            print(json.dumps(a))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Long-duration runtime soak checker for Delta 9 search API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--queries", nargs="+", default=["water tank", "pipes", "shoes"])
    parser.add_argument("--loops", type=int, default=6)
    parser.add_argument("--interval-sec", type=int, default=20)
    parser.add_argument("--min-count-alert", type=int, default=1)
    args = parser.parse_args()
    run_soak(args.base_url, args.queries, args.loops, args.interval_sec, args.min_count_alert)
