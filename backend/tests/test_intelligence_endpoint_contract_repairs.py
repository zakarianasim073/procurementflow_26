import asyncio

from app.api.v1.analytics import AnalyticsOverviewResponse, analytics_overview
from app.api.v1.government_portals import _query_tenders
from app.api.v1.intelligence import AgencyIntelResponse


class _AnalyticsService:
    async def get_lifecycle_stats(self):
        return {"total_records": 10, "matched_packages": 7}

    async def get_contractor_stats(self):
        return {"total_contractors": 4}

    async def get_agency_intelligence(self):
        return [{"agency_code": "BWDB"}]

    async def get_eexperience_stats(self, source):
        return {
            "total_records": 2 if source == "EEXPERIENCE_ALL" else 1,
            "total_value_bdt": 100.0,
            "unique_agencies": 1,
            "unique_contractors": 1,
            "delayed_records": 0,
        }


def test_analytics_overview_matches_flat_response_contract():
    payload = asyncio.run(analytics_overview(svc=_AnalyticsService(), user={}))
    validated = AnalyticsOverviewResponse(**payload)

    assert validated.total_tenders == 10
    assert validated.total_awards == 7
    assert validated.execution["completed_works"] == 2


def test_intelligence_response_accepts_list_payloads():
    validated = AgencyIntelResponse(data=[{"agency_code": "BWDB"}])

    assert validated.data == [{"agency_code": "BWDB"}]


class _Mappings:
    def all(self):
        return []


class _Result:
    def mappings(self):
        return _Mappings()


class _CaptureSession:
    statement = ""

    async def execute(self, statement, params):
        self.statement = str(statement)
        return _Result()


def test_government_portal_query_joins_current_source_tables():
    session = _CaptureSession()
    asyncio.run(_query_tenders(session, agency="BWDB", limit=10))

    assert "app_records" in session.statement
    assert "live_tender_sources" in session.statement
    assert "award_records_v2" in session.statement
    assert "pt.description" not in session.statement
