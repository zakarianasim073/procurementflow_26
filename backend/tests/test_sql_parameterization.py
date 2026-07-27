"""T-005 (SEC-04): SQL parameterization + CORS lockdown acceptance tests."""

import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

BACKEND = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class TestSqlAuditScript:
    def test_audit_returns_zero_findings(self):
        """Acceptance: the committed audit script exits 0 (zero unannotated findings)."""
        result = subprocess.run(
            [PYTHON, str(BACKEND / "scripts" / "audit_sql_interpolation.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"audit failed:\n{result.stdout}"

    def test_audit_detects_injected_fixture(self, tmp_path):
        """The audit actually catches an unannotated interpolated-SQL site."""
        fixture = BACKEND / "scripts" / "_t005_audit_fixture.py"
        fixture.write_text(
            'q = f"SELECT * FROM tenders WHERE id = {user_input}"\n',
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                [PYTHON, str(BACKEND / "scripts" / "audit_sql_interpolation.py")],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1
            assert "_t005_audit_fixture.py" in result.stdout
        finally:
            fixture.unlink()


class _RecordingSession:
    """Captures (sql, params) passed to execute()."""

    def __init__(self, rowcount=0, scalar=0):
        self.calls = []
        self._rowcount = rowcount
        self._scalar = scalar

    async def execute(self, stmt, params=None):
        self.calls.append((str(stmt), params))

        class _Result:
            rowcount = self._rowcount

            def scalar(inner):
                return self._scalar

        return _Result()

    async def commit(self):
        pass

    async def rollback(self):
        pass


class TestDataRetentionParameterized:
    @pytest.mark.asyncio
    async def test_enforce_binds_cutoff_and_batch_size(self):
        from app.core.data_retention import DataRetentionManager, RetentionPolicy

        manager = DataRetentionManager()
        manager.register_policy(RetentionPolicy("agent_results", 30, time_column="created_at"))
        session = _RecordingSession(rowcount=0)

        await manager.enforce(session, "agent_results")

        assert session.calls, "enforce() did not execute any statement"
        sql, params = session.calls[0]
        assert ":cutoff" in sql and ":batch_size" in sql
        assert "cutoff" in params and "batch_size" in params
        assert isinstance(params["cutoff"], datetime)
        # No inline timestamp literal in the SQL
        assert str(params["cutoff"].year) not in sql

    @pytest.mark.asyncio
    async def test_estimate_rows_binds_cutoff(self):
        from app.core.data_retention import DataRetentionManager, RetentionPolicy

        manager = DataRetentionManager()
        manager.register_policy(RetentionPolicy("agent_results", 30, time_column="created_at"))
        session = _RecordingSession(scalar=42)

        count = await manager.estimate_rows(session, "agent_results")

        assert count == 42
        sql, params = session.calls[0]
        assert ":cutoff" in sql
        assert "cutoff" in params


class TestBrainRouterBoundLimitOffset:
    def test_list_tenders_source_has_no_interpolated_limit(self):
        """LIMIT/OFFSET must be bound params, not f-string interpolation."""
        source = (BACKEND / "app" / "api" / "brain_router.py").read_text(encoding="utf-8")
        assert "LIMIT {int(limit)}" not in source
        assert "OFFSET {int(offset)}" not in source
        assert "LIMIT :lim OFFSET :off" in source


class TestCorsLockdown:
    def test_no_wildcard_in_allow_headers(self):
        from app.main import app
        from fastapi.middleware.cors import CORSMiddleware

        cors = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
        allow_headers = cors.kwargs.get("allow_headers", [])
        assert "*" not in allow_headers
        assert "Authorization" in allow_headers

    def test_origins_are_explicit(self):
        from app.main import app
        from fastapi.middleware.cors import CORSMiddleware

        cors = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
        origins = cors.kwargs.get("allow_origins", [])
        assert "*" not in origins
