from app.api.v1 import system
from app.core.security import get_current_user


def test_admin_rebuild_enqueues_celery_task(monkeypatch):
    class FakeTask:
        id = "maintenance-job"

    monkeypatch.setattr(
        "app.workers.tasks.maintenance_tasks.run_admin_maintenance_task.delay",
        lambda action: FakeTask(),
    )

    result = system._enqueue_admin_task("rebuild_lifecycle")

    assert result == {
        "success": True,
        "message": "rebuild_lifecycle queued",
        "job_id": "maintenance-job",
        "status": "processing",
    }


def test_admin_rebuild_routes_require_role():
    routes = {
        route.path: route
        for route in system.router.routes
        if route.path.startswith("/admin/")
    }

    assert len(routes) == 4
    for route in routes.values():
        role_dependency = route.dependant.dependencies[0]
        assert any(
            nested.call is get_current_user
            for nested in role_dependency.dependencies
        )
