"""Typed exceptions for the EPDP client."""

from __future__ import annotations


class EPDPError(Exception):
    """Base exception for all EPDP client errors."""


class EPDPClientError(EPDPError):
    """Generic client error (non-auth, non-connection)."""


class EPDPConnectionError(EPDPError):
    """Connection-level failure (DNS, timeout, refused)."""


class EPDPAuthError(EPDPError):
    """Authentication / authorisation failure (401 / 403)."""


class EPDPNotFoundError(EPDPError):
    """Resource not found (404)."""


class EPDPValidationError(EPDPError):
    """Request validation failure (422)."""
