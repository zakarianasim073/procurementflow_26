"""T-003 (SEC-01): JWT secret must come from the environment outside dev.

Acceptance criteria under test:
- Non-dev boot without JWT_SECRET aborts with a named-variable error.
- Tokens sign/verify via the env-provided secret (no .jwt_secret file involved).
- Dev mode still resolves a secret without manual setup.
"""
from __future__ import annotations

import pytest

from app.core.config import get_persistent_jwt_secret, settings
from app.core.security import create_token, decode_token


def test_production_without_jwt_secret_aborts(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        get_persistent_jwt_secret()


@pytest.mark.parametrize("environment", ["production", "staging", "prod-eu", "PRODUCTION"])
def test_all_non_dev_environments_require_env_secret(monkeypatch, environment):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("ENVIRONMENT", environment)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        get_persistent_jwt_secret()


def test_env_secret_wins_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "env-secret-for-test")
    assert get_persistent_jwt_secret() == "env-secret-for-test"


def test_dev_mode_boots_without_manual_setup(monkeypatch, tmp_path):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setattr("app.core.config._jwt_secret_file", tmp_path / ".jwt_secret")
    secret = get_persistent_jwt_secret()
    assert secret
    # Second call returns the same persisted secret, not a fresh one.
    assert get_persistent_jwt_secret() == secret


def test_token_round_trip_with_env_secret(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "round-trip-secret")
    token = create_token("t003-user")
    payload = decode_token(token)
    assert payload["sub"] == "t003-user"
