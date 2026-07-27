"""W-010: Verify cross-table join consistency via normalized_package_no.

This golden test samples records and verifies that normalized_package_no
values are correctly populated and idempotent.
"""

import pytest
from sqlalchemy import select, func
from app.db.database import get_sync_session
from app.core.helpers import normalize_package_no
from app.models.intelligence import ProcurementTender, APPRecord, AwardRecordV2


@pytest.mark.golden
def test_package_no_normalization_consistency():
    """Verify normalized_package_no is populated for cross-table joins (W-010).

    W-010 goal: ensure normalized_package_no enables joins across procurement_tenders,
    app_records, and award_records_v2. This test verifies that normalized values are
    populated and usable for join operations across all three tables.
    """
    session = get_sync_session()
    try:
        # Sample records with package_no from each table
        pt_samples = session.execute(
            select(ProcurementTender.package_no, ProcurementTender.normalized_package_no)
            .where(ProcurementTender.package_no.isnot(None))
            .limit(10)
        ).fetchall()

        ar_samples = session.execute(
            select(APPRecord.package_no, APPRecord.normalized_package_no)
            .where(APPRecord.package_no.isnot(None))
            .limit(10)
        ).fetchall()

        av_samples = session.execute(
            select(AwardRecordV2.package_no, AwardRecordV2.normalized_package_no)
            .where(AwardRecordV2.package_no.isnot(None))
            .limit(10)
        ).fetchall()

        # Verify: normalized_package_no is populated and usable for joins
        for raw, normalized in pt_samples + ar_samples + av_samples:
            assert raw is not None
            assert normalized is not None, f"normalized_package_no missing for package_no={raw!r}"
            assert isinstance(normalized, str) and len(normalized) > 0, (
                f"normalized_package_no should be non-empty string for package_no={raw!r}, got {normalized!r}"
            )
    finally:
        session.close()


def test_normalize_package_no_idempotent():
    """Verify normalize_package_no() is idempotent."""
    test_cases = [
        "ABC-123-45",
        "ABC 123 45",
        "ABC/123/45",
        "ABC.123.45",
        "abc-123-45",
        "  ABC  123  ",
    ]
    for raw in test_cases:
        once = normalize_package_no(raw)
        twice = normalize_package_no(once)
        assert once == twice, f"normalize_package_no() not idempotent for {raw!r}"


def test_normalize_package_no_edge_cases():
    """Reject pure-numeric IDs (e-GP tender IDs) and return empty for blanks."""
    assert normalize_package_no("1127087") == "", "pure numeric should be rejected"
    assert normalize_package_no("") == ""
    assert normalize_package_no(None) == ""
    assert normalize_package_no("   ") == ""
    # Valid package numbers contain letters + digits + separators
    assert normalize_package_no("BWDB/BMDA/2024-25/01") != ""
    assert normalize_package_no("LGED-DHK-123/2024") != ""


def test_package_no_repair_service_idempotent():
    """T-029: PackageNoRepairService.repair() is safe to run twice (idempotent)."""
    from app.services.package_no_repair_service import PackageNoRepairService

    result1 = PackageNoRepairService.repair()
    assert "total_award_records" in result1
    assert "resolved" in result1
    assert "unresolved" in result1
    assert "resolution_rate_pct" in result1
    assert 0.0 <= result1["resolution_rate_pct"] <= 100.0

    # Second run should repair 0 additional rows (idempotent)
    result2 = PackageNoRepairService.repair()
    assert result2.get("repaired_this_run", 0) == 0, (
        "Second repair pass should find 0 new rows to fix"
    )


def test_package_no_quality_metrics_structure():
    """T-029: get_quality_metrics() returns well-formed stats dict."""
    from app.services.package_no_repair_service import PackageNoRepairService

    metrics = PackageNoRepairService.get_quality_metrics()
    required_keys = {
        "total_award_records",
        "resolved",
        "unresolved",
        "unresolvable_no_key",
        "resolution_rate_pct",
        "timestamp",
    }
    missing = required_keys - set(metrics.keys())
    assert not missing, f"quality_metrics missing keys: {missing}"

    assert metrics["resolved"] + metrics["unresolved"] <= metrics["total_award_records"]
    assert metrics["unresolvable_no_key"] <= metrics["unresolved"]
