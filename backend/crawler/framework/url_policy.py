"""Outbound URL policy for crawler-controlled HTTP requests."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from .config import settings


class UnsafeCrawlerURL(ValueError):
    """Raised when a crawler URL violates the outbound-network policy."""


def _allowed_hosts() -> set[str]:
    hosts: set[str] = set()
    for base in (settings.e_gp_base_url, settings.bppa_base_url):
        host = (urlparse(base).hostname or "").lower().rstrip(".")
        if host:
            hosts.add(host)
    return hosts


def validate_crawler_url(url: str) -> str:
    """Require HTTPS and an explicitly configured public procurement host."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise UnsafeCrawlerURL("crawler URL must be credential-free HTTPS")
    if parsed.port not in (None, 443):
        raise UnsafeCrawlerURL("crawler URL must use the standard HTTPS port")
    if host not in _allowed_hosts():
        raise UnsafeCrawlerURL(f"crawler host is not allow-listed: {host}")

    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }
    except (OSError, ValueError) as exc:
        raise UnsafeCrawlerURL(f"crawler host could not be resolved: {host}") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise UnsafeCrawlerURL("crawler host resolved to a non-public address")
    return url

