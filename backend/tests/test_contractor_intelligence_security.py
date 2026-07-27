from __future__ import annotations

from pathlib import Path


def test_contractor_intelligence_routers_do_not_embed_db_credentials():
    backend = Path(__file__).resolve().parents[1]
    router_files = [
        backend / "app" / "api" / "v1" / "contractor_intelligence.py",
        backend / "app" / "api" / "v1" / "tender_matching.py",
        backend / "app" / "api" / "v1" / "capacity_risk.py",
    ]
    forbidden = ["password=", "procurementflow", "user=\"postgres\"", "user='postgres'"]
    for router_file in router_files:
        source = router_file.read_text(encoding="utf-8")
        for value in forbidden:
            assert value not in source, f"{router_file.name} embeds database credential fragment: {value}"
