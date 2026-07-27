from fastapi.routing import APIRoute

from app.api.v1.agents import router
from app.core.security import get_current_user


def test_agent_metadata_routes_require_authentication():
    protected_paths = {
        "/agents/registered",
        "/agents/brain-status",
        "/agents/recent-runs",
        "/agents/pipeline-phases",
        "/agents/{agent_id}",
    }

    routes = {
        route.path: route
        for route in router.routes
        if isinstance(route, APIRoute) and route.path in protected_paths
    }

    assert routes.keys() == protected_paths
    for route in routes.values():
        assert any(
            dependency.call is get_current_user
            for dependency in route.dependant.dependencies
        )
