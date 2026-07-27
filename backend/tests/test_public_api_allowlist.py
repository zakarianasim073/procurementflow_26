from app.main import _is_public_api_path


def test_sensitive_api_namespaces_are_not_public():
    protected_paths = {
        "/api/tender/list",
        "/api/tenders",
        "/api/boq/compare",
        "/api/agents/registered",
        "/api/brain/status",
        "/api/ppr2025/evaluate/works",
        "/api/crawler/test-searchservlet",
    }

    assert all(not _is_public_api_path(path) for path in protected_paths)


def test_required_bootstrap_endpoints_remain_public():
    public_paths = {
        "/api/health",
        "/api/ready",
        "/api/live",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/v2/sso/oidc/init",
        "/api/v2/sso/oidc/callback",
        "/api/v2/sso/saml/acs",
    }

    assert all(_is_public_api_path(path) for path in public_paths)
