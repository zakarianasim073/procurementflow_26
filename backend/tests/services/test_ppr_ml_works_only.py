from sqlalchemy.dialects import postgresql

from app.services.ppr_ml_service import _verified_works_opening_stmt


def test_opening_report_training_query_requires_certified_works_provenance():
    sql = str(
        _verified_works_opening_stmt().compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()

    assert "exists" in sql
    assert "procurement_lifecycle" in sql
    assert "procurement_tenders" in sql
    assert "app_records" in sql
    assert "lower(trim(app_records.category)) = 'works'" in sql
