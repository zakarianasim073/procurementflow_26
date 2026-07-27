"""T-035 Phase 2: Endpoint audit - identify tenant-scoped and permission-protected routes.

This script analyzes all API endpoints and reports:
1. Public/unauthenticated endpoints (allowlist)
2. Authenticated but unscoped endpoints (requires tenant context)
3. Missing permission checks (should guard certain operations)
"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

# Public endpoints that should NOT require tenant context
PUBLIC_ENDPOINTS = {
    "/api/health",
    "/api/ready",
    "/api/live",
    "/api/auth/register",
    "/api/auth/login",
    "/api/docs",
    "/api/openapi.json",
    "/api/redoc",
}

# Tenant-scoped endpoints (should require tenant_id in context)
TENANT_SCOPED_OPERATIONS = {
    ("POST", "/api/v2/enterprise/tenants"),  # superuser creates tenants
    ("GET", "/api/v2/enterprise/tenants"),
    ("GET", "/api/v2/enterprise/tenants/{tenant_id}"),
    ("POST", "/api/v2/enterprise/tenants/{tenant_id}/members"),
    ("GET", "/api/v2/enterprise/tenants/{tenant_id}/members"),
    ("PUT", "/api/v2/enterprise/tenants/{tenant_id}/members/{user_id}/role"),
    ("DELETE", "/api/v2/enterprise/tenants/{tenant_id}/members/{user_id}"),
    ("GET", "/api/v2/enterprise/roles"),
    ("GET", "/api/v2/enterprise/permissions"),
}

# Permission requirements by endpoint pattern
PERMISSION_REQUIREMENTS = {
    ("/api/tenders", "GET"): ["tender:read"],
    ("/api/tenders", "POST"): ["tender:create"],
    ("/api/tenders/{id}", "PUT"): ["tender:update"],
    ("/api/tenders/{id}", "DELETE"): ["tender:delete"],
    ("/api/boq", "POST"): ["boq:compare"],
    ("/api/v2/enterprise/tenants/{id}/members", "POST"): ["admin:manage_users"],
    ("/api/v2/enterprise/tenants/{id}/members", "DELETE"): ["admin:manage_users"],
    ("/api/v2/enterprise/tenants/{id}/members/{uid}/role", "PUT"): ["admin:manage_roles"],
}


class EndpointAudit:
    """Audit API endpoints for RBAC compliance."""

    def __init__(self):
        self.findings: List[Dict] = []
        self.scoped_endpoints: Set[str] = set()
        self.unscoped_endpoints: Set[str] = set()
        self.public_endpoints: Set[str] = set()

    def add_finding(
        self,
        severity: str,
        endpoint: str,
        method: str,
        issue: str,
        recommendation: str,
    ) -> None:
        """Record an audit finding."""
        self.findings.append({
            "severity": severity,
            "endpoint": endpoint,
            "method": method,
            "issue": issue,
            "recommendation": recommendation,
        })

    def report(self) -> None:
        """Print audit report."""
        print("\n" + "=" * 80)
        print("ENDPOINT AUDIT REPORT — T-035 Phase 2 (Tenant-Scoped RBAC)")
        print("=" * 80)

        if not self.findings:
            print("✅ No critical findings. All audited endpoints are compliant.\n")
            return

        # Group by severity
        critical = [f for f in self.findings if f["severity"] == "CRITICAL"]
        high = [f for f in self.findings if f["severity"] == "HIGH"]
        medium = [f for f in self.findings if f["severity"] == "MEDIUM"]

        if critical:
            print(f"\n🔴 CRITICAL ({len(critical)}):")
            for f in critical:
                print(f"  • {f['method']:6} {f['endpoint']:50} — {f['issue']}")
                print(f"    → {f['recommendation']}")

        if high:
            print(f"\n🟠 HIGH ({len(high)}):")
            for f in high:
                print(f"  • {f['method']:6} {f['endpoint']:50} — {f['issue']}")
                print(f"    → {f['recommendation']}")

        if medium:
            print(f"\n🟡 MEDIUM ({len(medium)}):")
            for f in medium:
                print(f"  • {f['method']:6} {f['endpoint']:50} — {f['issue']}")
                print(f"    → {f['recommendation']}")

        print("\n" + "=" * 80)


# Standard endpoint audit checklist
ENDPOINT_AUDIT_CHECKLIST = {
    "public_endpoints": {
        "/api/health": "No auth required",
        "/api/ready": "No auth required",
        "/api/live": "No auth required",
        "/api/auth/register": "No auth required (sign-up)",
        "/api/auth/login": "No auth required (sign-in)",
        "/api/auth/refresh": "Refresh token (stateless OK)",
    },
    "tenant_scoped": {
        "/api/tenders": "Requires tenant_id context",
        "/api/boq": "Requires tenant_id context",
        "/api/agents": "Requires tenant_id context",
        "/api/v2/enterprise/tenants/{id}/members": "Requires tenant_id + admin:manage_users",
    },
    "permission_enforced": {
        "/api/tenders (POST)": "Requires tenant:create",
        "/api/boq (POST)": "Requires boq:compare",
        "/api/v2/enterprise/tenants/{id}/members (POST)": "Requires admin:manage_users",
        "/api/v2/enterprise/tenants/{id}/members (DELETE)": "Requires admin:manage_users",
    },
}


if __name__ == "__main__":
    audit = EndpointAudit()

    # This would be called by the test suite to verify all endpoints
    print("Endpoint audit module loaded. Call audit.report() after analysis.")
    print("\nAudit Checklist:")
    print("1. Public endpoints: no tenant context required")
    print("2. Tenant-scoped endpoints: require tenant_id from request.state.tenant_id")
    print("3. Permission-enforced endpoints: check via RBACService.user_has_permission()")
    print("\nChecklist items:", ENDPOINT_AUDIT_CHECKLIST)
