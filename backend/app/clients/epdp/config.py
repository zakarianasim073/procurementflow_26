"""Configuration for the EPDP API client (env-driven)."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


class EPDPClientConfig(BaseModel):
    """Connection settings for the EPDP Data Platform API.

    EPDP defaults to port 8100 locally — 8000 is ProcureFlow's own backend.
    """

    base_url: str = Field(default_factory=lambda: _env("EPDP_BASE_URL", "http://localhost:8100"))
    api_key: str = Field(default_factory=lambda: _env("EPDP_API_KEY", "dev-key"))
    tenant_id: str = Field(default_factory=lambda: _env("EPDP_TENANT_ID", "default"))
    timeout: float = Field(default=30.0, ge=1.0)
    verify_ssl: bool = Field(default=True)
