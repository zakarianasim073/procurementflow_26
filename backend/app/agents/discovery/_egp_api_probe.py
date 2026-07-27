from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.egp_client import eGPClient


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def main() -> int:
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    client = eGPClient(
        email=str(request.get("email", "")),
        password=str(request.get("password", "")),
        timeout=30,
    )
    authenticated = client.login()
    if request.get("action") == "login":
        response = {
            "success": authenticated,
            "session_active": client.session.is_authenticated,
        }
    elif request.get("action") == "search":
        response = {
            "authenticated": authenticated,
            "results": client.search_tenders(
                tender_id=str(request.get("tender_id", "")),
            ) if authenticated else [],
        }
    else:
        return 2
    sys.stdout.write(json.dumps(_jsonable(response), default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
