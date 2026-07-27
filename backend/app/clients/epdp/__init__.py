"""EPDP Data Platform typed client (contract: Enterprise_OS/contracts/API/openapi.json)."""

from app.clients.epdp.client import EPDPClient
from app.clients.epdp.config import EPDPClientConfig
from app.clients.epdp.errors import (
    EPDPAuthError,
    EPDPClientError,
    EPDPConnectionError,
    EPDPError,
    EPDPNotFoundError,
    EPDPValidationError,
)
from app.clients.epdp.models import (
    HealthResponse,
    KnowledgeHealthResponse,
    TenderHealthResponse,
)

__all__ = [
    "EPDPClient",
    "EPDPClientConfig",
    "EPDPError",
    "EPDPClientError",
    "EPDPConnectionError",
    "EPDPAuthError",
    "EPDPNotFoundError",
    "EPDPValidationError",
    "HealthResponse",
    "KnowledgeHealthResponse",
    "TenderHealthResponse",
]
