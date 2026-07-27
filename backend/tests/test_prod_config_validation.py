"""T-008 (INF-03): production config validation matrix."""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

SNIPPET = """
import os
os.environ["ENVIRONMENT"] = {env!r}
for var, val in {vars!r}.items():
    if val is None:
        os.environ.pop(var, None)
    else:
        os.environ[var] = val
# Neutralize .env loading so the matrix controls the environment exactly
import dotenv
dotenv.load_dotenv = lambda *a, **k: None
try:
    from app.core.config import settings
    print("BOOT_OK")
except RuntimeError as e:
    print(f"BOOT_FAIL: {{e}}")
"""


def _boot(env: str, **vars):
    code = SNIPPET.format(env=env, vars=vars)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=BACKEND)
    return r.stdout + r.stderr


GOOD = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5433/db",
    "JWT_SECRET": "test-secret",
    "JWT_REFRESH_SECRET": "test-refresh-secret",
    "REDIS_URL": "redis://localhost:6379/0",
}


class TestProductionValidation:
    def test_prod_all_present_boots(self):
        out = _boot("production", **GOOD)
        assert "BOOT_OK" in out

    def test_prod_missing_database_url_names_it(self):
        out = _boot("production", **{**GOOD, "DATABASE_URL": None})
        assert "BOOT_FAIL" in out and "DATABASE_URL" in out

    def test_prod_missing_redis_url_names_it(self):
        out = _boot("production", **{**GOOD, "REDIS_URL": None})
        assert "BOOT_FAIL" in out and "REDIS_URL" in out

    def test_prod_missing_jwt_secret_names_it(self):
        out = _boot("production", **{**GOOD, "JWT_SECRET": None})
        assert ("BOOT_FAIL" in out or "RuntimeError" in out) and "JWT_SECRET" in out

    def test_prod_missing_multiple_names_all(self):
        out = _boot("production", **{**GOOD, "DATABASE_URL": None, "REDIS_URL": None})
        assert "DATABASE_URL" in out and "REDIS_URL" in out

    def test_staging_gated_too(self):
        out = _boot("staging", **{**GOOD, "REDIS_URL": None})
        assert "BOOT_FAIL" in out and "REDIS_URL" in out

    def test_dev_boots_without_required_vars(self):
        out = _boot("development", DATABASE_URL=None, REDIS_URL=None)
        assert "BOOT_OK" in out
