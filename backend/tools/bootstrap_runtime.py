from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.security import create_token  # noqa: E402
from recalculate_nppi import main as recalculate_nppi  # noqa: E402


BACKEND_URL = os.getenv("PROCUREFLOW_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_URL = os.getenv("PROCUREFLOW_FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
RUNTIME_DIR = BACKEND / "runtime" / "startup"


def _request(
    method: str,
    url: str,
    body: Optional[Dict[str, Any]] = None,
    token: str = "",
    timeout: int = 30,
) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            content_type = resp.headers.get("content-type", "")
            parsed: Any
            if "application/json" in content_type:
                parsed = json.loads(raw.decode("utf-8") or "{}")
            else:
                parsed = raw.decode("utf-8", errors="replace")[:500]
            return {
                "ok": 200 <= resp.status < 400,
                "status": resp.status,
                "elapsed_ms": round((time.time() - started) * 1000, 2),
                "data": parsed,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": exc.code,
            "elapsed_ms": round((time.time() - started) * 1000, 2),
            "error": raw[:1000],
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": 0,
            "elapsed_ms": round((time.time() - started) * 1000, 2),
            "error": str(exc),
        }


def _wait_for(url: str, timeout_seconds: int = 90) -> Dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last: Dict[str, Any] = {}
    while time.time() < deadline:
        last = _request("GET", url, timeout=5)
        if last.get("ok"):
            return {"ready": True, **last}
        time.sleep(2)
    return {"ready": False, **last}


def _summarize_response(value: Dict[str, Any]) -> Dict[str, Any]:
    data = value.get("data")
    summary = {k: v for k, v in value.items() if k != "data"}
    if isinstance(data, dict):
        summary["keys"] = list(data.keys())[:20]
        if "data" in data and isinstance(data["data"], dict):
            summary["data_keys"] = list(data["data"].keys())[:20]
        for key in ("status", "success", "total", "agents_registered", "knowledge_entries", "knowledge_cache_loaded"):
            if key in data:
                summary[key] = data[key]
    else:
        summary["data_preview"] = str(data)[:200]
    return summary


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    token = create_token("owner-zakaria-nasim", "enterprise")
    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backend_url": BACKEND_URL,
        "frontend_url": FRONTEND_URL,
        "ollama_url": OLLAMA_URL,
        "checks": {},
        "actions": {},
    }

    report["checks"]["backend_ready"] = _wait_for(f"{BACKEND_URL}/docs", timeout_seconds=120)
    report["checks"]["frontend_ready"] = _wait_for(f"{FRONTEND_URL}/index.html", timeout_seconds=90)

    ollama = _request("GET", f"{OLLAMA_URL}/api/tags", timeout=5)
    report["checks"]["ollama"] = ollama
    if ollama.get("ok") and isinstance(ollama.get("data"), dict):
        models = [m.get("name") for m in ollama["data"].get("models", []) if isinstance(m, dict)]
        report["checks"]["ollama_models"] = models

    try:
        recalculate_nppi()
        nppi_file = RUNTIME_DIR / "nppi_recalculation.json"
        report["actions"]["nppi_recalculation"] = json.loads(nppi_file.read_text(encoding="utf-8"))
    except Exception as exc:
        report["actions"]["nppi_recalculation"] = {"ok": False, "error": str(exc)}

    calls = [
        ("brain_status_before", "GET", "/api/brain/status", None, 20, False),
        ("brain_bootstrap_memory", "POST", "/api/brain/bootstrap-memory?force=false&include_db_knowledge=true", None, 120, False),
        ("brain_sync_knowledge", "POST", "/api/brain/sync-knowledge?limit=5000", None, 120, False),
        (
            "brain_broadcast_processing",
            "POST",
            "/api/brain/broadcast",
            {
                "sender_id": "startup-bat",
                "subject": "startup_data_processing",
                "body": {
                    "action": "process_runtime_data",
                    "tasks": ["nppi_recalculate", "knowledge_sync", "ppr_ml_check", "slt_win_prediction"],
                    "use_ollama": bool(report["checks"]["ollama"].get("ok")),
                },
            },
            30,
            False,
        ),
        ("ppr_model_status_before", "GET", "/api/ppr2025/model/status", None, 60, True),
        ("ppr_model_train", "POST", "/api/ppr2025/model/train", {"force": os.getenv("PROCUREFLOW_FORCE_TRAIN", "0") == "1"}, int(os.getenv("PROCUREFLOW_TRAIN_TIMEOUT", "240")), True),
        (
            "ppr_slt_eval_sample",
            "POST",
            "/api/ppr2025/evaluate/slt",
            {
                "tender_id": "STARTUP-SLT-SMOKE",
                "estimated_cost": 10000000,
                "bid_price": 6900000,
                "agency": "BWDB",
                "zone": "Dhaka",
                "bidder_name": "Startup Smoke Bidder",
                "documents_complete": True,
                "qualification_passed": True,
                "responsive_bidders": [
                    {"bidder_name": "Startup Smoke Bidder", "quoted_amount": 6900000, "status": "responsive"},
                    {"bidder_name": "Market Bidder A", "quoted_amount": 8600000, "status": "responsive"},
                    {"bidder_name": "Market Bidder B", "quoted_amount": 9100000, "status": "responsive"},
                ],
            },
            120,
            True,
        ),
        (
            "ppr_model_explain_ollama",
            "POST",
            "/api/ppr2025/model/explain",
            {
                "estimated_cost": 10000000,
                "bid_price": 6900000,
                "bidder_count": 3,
                "agency": "BWDB",
                "zone": "Dhaka",
                "contractor_name": "Startup Smoke Bidder",
                "regime": "PPR2025",
            },
            120,
            True,
        ),
        ("ppr_overview", "GET", "/api/ppr2025/overview", None, 90, True),
        ("ppr_predictions", "GET", "/api/ppr2025/predictions", None, 60, True),
        ("ppr_evaluations", "GET", "/api/ppr2025/evaluations", None, 60, True),
        ("ppr_document_checklist", "GET", "/api/ppr2025/document-checklist", None, 30, True),
        ("ppr_nppi_summary", "GET", "/api/ppr2025/nppi-summary?limit=10", None, 90, True),
        ("brain_status_after", "GET", "/api/brain/status", None, 20, False),
        ("knowledge_graph_stats", "GET", "/api/knowledge-graph/stats", None, 60, False),
    ]
    if os.getenv("PROCUREFLOW_RUN_IDLE_CYCLE", "0") == "1":
        calls.insert(
            4,
            (
                "brain_idle_cycle",
                "POST",
                "/api/brain/idle-cycle",
                None,
                int(os.getenv("PROCUREFLOW_IDLE_TIMEOUT", "30")),
                False,
            ),
        )
    else:
        report["actions"]["brain_idle_cycle"] = {
            "ok": True,
            "status": "queued_via_broadcast",
            "note": "Skipped synchronous idle-cycle wait. Set PROCUREFLOW_RUN_IDLE_CYCLE=1 to run it during startup.",
        }

    for name, method, path, body, timeout, auth in calls:
        result = _request(method, f"{BACKEND_URL}{path}", body=body, token=token if auth else "", timeout=timeout)
        report["actions"][name] = result
        print(f"{name}: {json.dumps(_summarize_response(result), ensure_ascii=False)}", flush=True)

    report["summary"] = {
        "backend_ready": bool(report["checks"]["backend_ready"].get("ready")),
        "frontend_ready": bool(report["checks"]["frontend_ready"].get("ready")),
        "ollama_ready": bool(report["checks"]["ollama"].get("ok")),
        "failed_actions": [
            name for name, result in report["actions"].items()
            if isinstance(result, dict) and result.get("ok") is False
        ],
    }

    out = RUNTIME_DIR / "procureflow_startup_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Startup report: {out}")
    return 0 if report["summary"]["backend_ready"] and report["summary"]["frontend_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
