def test_warehouse_tasks_import_and_registration():
    from app.celery_app import celery_app
    from app.workers import warehouse_tasks

    expected = {
        warehouse_tasks.refresh_warehouse_facts.name,
        warehouse_tasks.refresh_warehouse_dimensions.name,
        warehouse_tasks.refresh_materialized_views.name,
        warehouse_tasks.get_warehouse_health_check.name,
    }

    assert expected <= set(celery_app.tasks)
