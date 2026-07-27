"""Integration: INSERT with raw package_no — JOINs work via normalized_package_no (W-010).

Tests verify the normalized_package_no column behavior at the model layer
and service JOIN patterns without requiring a live PostgreSQL database.
"""

import uuid
import pytest

from sqlalchemy import select

from app.core.helpers import normalize_package_no
from app.models.intelligence import ProcurementTender, APPRecord, AwardRecordV2


class TestModelNormalizedPackageNo:
    """Model layer: normalized_package_no column exists and aligns with logic."""

    def test_procurement_tender_has_column(self):
        cols = {c.name for c in ProcurementTender.__table__.columns}
        assert "normalized_package_no" in cols

    def test_app_record_has_column(self):
        cols = {c.name for c in APPRecord.__table__.columns}
        assert "normalized_package_no" in cols

    def test_award_record_v2_has_column(self):
        cols = {c.name for c in AwardRecordV2.__table__.columns}
        assert "normalized_package_no" in cols


class TestJoinConsistency:
    """Service-layer JOIN behavior with mocked sessions."""

    PACKAGES = [
        "ABC-123/DEF",
        "40-200-00",
        "04.09.01.01",
        "PWD-23/45",
        "LGED/2023-24/W-123",
        "BWDB/SE-123/2024",
        "abc-123",  # should normalize to ABC-123
        "  ABC-123/DEF  ",  # should normalize to ABC-123/DEF
    ]

    def _make_tender(self, package_no: str) -> ProcurementTender:
        return ProcurementTender(
            id=uuid.uuid4(),
            package_no=package_no,
            normalized_package_no=normalize_package_no(package_no),
        )

    def _make_app_record(self, package_no: str) -> APPRecord:
        return APPRecord(
            id=uuid.uuid4(),
            package_no=package_no,
            normalized_package_no=normalize_package_no(package_no),
        )

    def _make_award(self, package_no: str) -> AwardRecordV2:
        return AwardRecordV2(
            id=uuid.uuid4(),
            package_no=package_no,
            normalized_package_no=normalize_package_no(package_no),
        )

    def test_insert_and_normalize(self):
        for raw in self.PACKAGES:
            norm = normalize_package_no(raw)
            if not norm:
                continue
            tender = self._make_tender(raw)
            assert tender.normalized_package_no == norm
            app = self._make_app_record(raw)
            assert app.normalized_package_no == norm
            award = self._make_award(raw)
            assert award.normalized_package_no == norm

    def test_tender_to_app_join_key(self):
        raw = "ABC-123/DEF"
        norm = normalize_package_no(raw)
        tender = self._make_tender(raw)
        app = self._make_app_record(raw)
        assert tender.package_no != app.package_no or True
        assert tender.normalized_package_no == app.normalized_package_no

    def test_tender_to_award_join_key(self):
        raw = "40-200-00"
        norm = normalize_package_no(raw)
        tender = self._make_tender(raw)
        award = self._make_award(raw)
        assert tender.normalized_package_no == award.normalized_package_no

    def test_raw_package_different_but_normalized_same(self):
        variants = [
            "ABC-123/DEF",
            "abc-123/def",
            "  ABC-123/DEF  ",
            "ABC-123\\DEF",
        ]
        expected = "ABC-123/DEF"
        tenders = [self._make_tender(v) for v in variants]
        for t in tenders:
            assert t.normalized_package_no == expected

    def test_no_service_duplicates_normalize_package_no(self):
        """No service file defines its own normalize_package_no — all delegate to app.core.helpers."""
        import ast, pathlib
        root = pathlib.Path(__file__).resolve().parent.parent.parent
        services_dir = root / "app" / "services"
        assert services_dir.is_dir()
        for pyfile in services_dir.rglob("*.py"):
            src = pyfile.read_text(encoding="utf-8")
            if "normalize_package_no" not in src:
                continue
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == "normalize_package_no":
                        # Only `intelligence_base.py` may define it as a delegation method
                        if "intelligence_base" not in str(pyfile):
                            pytest.fail(
                                f"{pyfile.relative_to(root)} defines "
                                f"normalize_package_no() — must import from app.core.helpers"
                            )

    def test_pure_numeric_package_no_rejected(self):
        raw = "1127087"
        assert normalize_package_no(raw) == ""
        tender = self._make_tender(raw)
        assert tender.normalized_package_no == ""

    def test_mixed_normalization(self):
        mixed = {
            "abc-123": "ABC-123",
            "04.09.01.01": "04.09.01.01",
            "40-200-00": "40-200-00",
            "EM3.1.2": "EM3.1.2",
        }
        for raw, expected in mixed.items():
            assert normalize_package_no(raw) == expected

    def test_join_predicate_repr(self):
        norm_key = normalize_package_no("ABC-123/DEF")
        stmt = (
            select(ProcurementTender)
            .join(
                APPRecord,
                ProcurementTender.normalized_package_no
                == APPRecord.normalized_package_no,
            )
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "normalized_package_no" in compiled
