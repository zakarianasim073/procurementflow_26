from __future__ import annotations

import inspect

import pytest

from app.services.intelligence.domain.services.award_service import AwardService
from app.services.intelligence.domain.services.discovery_service import DiscoveryService
from app.services.intelligence_data_service_facade import IntelligenceDataServiceFacade


class FakeAPPNOA:
    def __init__(self):
        self.calls = []

    async def list_awards_for_agent(self, agency="", limit=100):
        self.calls.append(("list", agency, limit))
        return [{"agency": agency, "limit": limit}]

    async def reconcile_award_package_mapping_from_json(self, flat_path, progress=None):
        self.calls.append(("package", flat_path, progress))
        return 7

    async def reconcile_awards_to_app_records(self, progress=None):
        self.calls.append(("reconcile", progress))
        return {"matched": 3}

    async def get_award_data_quality_stats(self):
        self.calls.append(("quality",))
        return {"total_awards": 11}


class FakeDB:
    async def execute(self, stmt):
        class Result:
            def scalar(self):
                return 5
        return Result()


class FakeTender:
    def __init__(self):
        self.calls = []

    async def search_live_tenders(self, **kwargs):
        self.calls.append(("search", kwargs))
        return {"records": []}

    async def get_live_tender_stats(self, agency=None):
        self.calls.append(("stats", agency))
        return {"agency": agency}

    async def import_lifecycle_from_json(self, json_path=None, progress=None):
        self.calls.append(("lifecycle", json_path, progress))
        return 1

    async def backfill_tender_regimes(self):
        self.calls.append(("regimes",))
        return {"updated": 2}


class FakeContractor:
    def __init__(self):
        self.calls = []

    async def get_contractor_stats(self):
        self.calls.append(("stats",))
        return {"total_contractors": 4}

    async def get_contractor_performance(self, contractor_name, source=None):
        self.calls.append(("performance", contractor_name, source))
        return {"contractor": contractor_name, "source": source}


class FakeCompetitor:
    def __init__(self):
        self.calls = []

    async def get_npp_trends(self, months=12):
        self.calls.append(("npp", months))
        return [{"month": "2026-01"}]

    async def get_discount_patterns(self, agency=None, zone=None):
        self.calls.append(("discount", agency, zone))
        return []


@pytest.mark.asyncio
async def test_award_service_routes_app_noa_methods_to_app_noa():
    svc = AwardService.__new__(AwardService)
    svc._app_noa = FakeAPPNOA()
    svc.db = FakeDB()

    assert await svc.list_awards_for_agent("BWDB", 5) == [{"agency": "BWDB", "limit": 5}]
    assert await svc.reconcile_award_package_mapping_from_json("flat.json") == 7
    assert await svc.reconcile_awards_to_app_records(progress="p") == {"matched": 3}
    # get_award_data_quality_stats does actual DB queries, not delegation to _app_noa
    stats = await svc.get_award_data_quality_stats()
    assert "total_awards" in stats
    assert "distinct_packages" in stats

    assert svc._app_noa.calls == [
        ("list", "BWDB", 5),
        ("package", "flat.json", None),
        ("reconcile", "p"),
    ]


@pytest.mark.asyncio
async def test_discovery_service_routes_award_reconciliation_to_app_noa():
    svc = DiscoveryService.__new__(DiscoveryService)
    svc._app_noa = FakeAPPNOA()

    assert await svc.reconcile_award_package_mapping_from_json("flat.json") == 7
    assert await svc.reconcile_awards_to_app_records() == {"matched": 3}


@pytest.mark.asyncio
async def test_facade_award_listing_normalizes_legacy_arguments():
    facade = IntelligenceDataServiceFacade(db=None)
    facade._award = AwardService.__new__(AwardService)
    facade._award._app_noa = FakeAPPNOA()

    result = await facade.list_awards_for_agent(filters={"agency_code": "RHD"}, limit=9)

    assert result == [{"agency": "RHD", "limit": 9}]


def test_extracted_award_get_or_create_tender_has_no_flush_call():
    source = inspect.getsource(AwardService._get_or_create_tender)
    assert "await self.db.flush()" not in source


@pytest.mark.asyncio
async def test_facade_route_facing_methods_normalize_keywords():
    facade = IntelligenceDataServiceFacade(db=None)
    facade._tender = FakeTender()
    facade._contractor = FakeContractor()
    facade._competitor = FakeCompetitor()

    await facade.search_live_tenders(department_id="BWDB", office_id="X", keyword="bridge", page=2, page_size=25)
    await facade.get_live_tender_stats(agency="RHD")
    await facade.import_lifecycle_from_json()
    await facade.backfill_tender_regimes(progress="ignored")
    await facade.get_contractor_stats(contractor_id="ignored")
    await facade.get_contractor_performance(contractor_name="ABC", source="EEXPERIENCE_ALL")
    await facade.get_npp_trends(months=24)
    await facade.get_discount_patterns(agency="BWDB", zone="Khulna")

    assert facade._tender.calls == [
        ("search", {"department_id": "BWDB", "office_id": "X", "keyword": "bridge", "page": 2, "page_size": 25}),
        ("stats", "RHD"),
        ("lifecycle", None, None),
        ("regimes",),
    ]
    assert facade._contractor.calls == [
        ("stats",),
        ("performance", "ABC", "EEXPERIENCE_ALL"),
    ]
    assert facade._competitor.calls == [
        ("npp", 24),
        ("discount", "BWDB", "Khulna"),
    ]



@pytest.mark.asyncio
async def test_intelligence_base_service_build_works_record():
    """build_works_record should be inherited from IntelligenceBaseService."""
    from app.services.intelligence_base import IntelligenceBaseService
    from datetime import datetime, timezone

    # Create a minimal mock instance with the required helpers
    class MockBase(IntelligenceBaseService):
        def __init__(self):
            pass  # skip DB init

    svc = MockBase()
    record = svc.build_works_record(
        lifecycle=None,
        tender=None,
        app_record=None,
        live_record=None,
        award_record=None,
        opening_report=None,
    )

    assert record["schema_version"] == "2026-06-28"
    assert record["tender_id"] == "None"
    assert record["package_no"] == ""
    assert record["work_type"] == "Works"
    assert record["status"] == "Unknown"
    assert "extracted_at" in record


@pytest.mark.asyncio
async def test_intelligence_base_service_derive_discount_pct():
    from app.services.intelligence_base import IntelligenceBaseService

    class MockBase(IntelligenceBaseService):
        def __init__(self):
            pass

    svc = MockBase()
    assert svc._derive_discount_pct(100.0, 80.0, 0.8) == 20.0
    assert svc._derive_discount_pct(100.0, 80.0, 0.0) == 20.0
    assert svc._derive_discount_pct(0.0, 80.0, 0.0) == 0.0
    assert svc._derive_discount_pct(100.0, 0.0, 0.0) == 0.0


@pytest.mark.asyncio
async def test_intelligence_base_service_derive_record_status():
    from app.services.intelligence_base import IntelligenceBaseService

    class MockBase(IntelligenceBaseService):
        def __init__(self):
            pass

    svc = MockBase()
    assert svc._derive_record_status(live_status="Open") == "Open"
    assert svc._derive_record_status(winner="ABC Corp") == "Awarded"
    assert svc._derive_record_status(award_amount=100.0) == "Awarded"
    assert svc._derive_record_status(opening_report={}) == "Opened"
    assert svc._derive_record_status() == "Unknown"


@pytest.mark.asyncio
async def test_intelligence_base_service_normalize_responsive_bidders():
    from app.services.intelligence_base import IntelligenceBaseService

    class MockBase(IntelligenceBaseService):
        def __init__(self):
            pass

    svc = MockBase()
    bidders = [
        {"bidder_name": "A", "quoted_amount": 100, "discount_pct": 5, "rank": 2},
        {"name": "B", "final_amount": 90, "discount": 10, "rank": 1},
        {"contractor_name": "C", "amount": 110, "discount_percent": 0},
    ]
    result = svc._normalize_responsive_bidders(bidders)
    assert len(result) == 3
    assert result[0]["name"] == "B"
    assert result[0]["rank"] == 1
    assert result[1]["name"] == "A"
    assert result[1]["rank"] == 2


def test_domain_services_inherit_intelligence_base():
    """All domain services should inherit from IntelligenceBaseService."""
    from app.services.intelligence_base import IntelligenceBaseService
    from app.services.intelligence.domain.services.discovery_service import DiscoveryService
    from app.services.intelligence.domain.services.tender_service import TenderService
    from app.services.intelligence.domain.services.award_service import AwardService
    from app.services.intelligence.domain.services.contractor_service import ContractorService
    from app.services.intelligence.domain.services.competitor_service import CompetitorService
    from app.services.intelligence.domain.services.dashboard_service import DashboardService

    assert issubclass(DiscoveryService, IntelligenceBaseService)
    assert issubclass(TenderService, IntelligenceBaseService)
    assert issubclass(AwardService, IntelligenceBaseService)
    assert issubclass(ContractorService, IntelligenceBaseService)
    assert issubclass(CompetitorService, IntelligenceBaseService)
    assert issubclass(DashboardService, IntelligenceBaseService)


def test_backfill_tender_regimes_uses_batch_update():
    """backfill_tender_regimes should collect updates and execute once, not per-row."""
    from app.services.intelligence.domain.services.tender_service import TenderService

    source = inspect.getsource(TenderService.backfill_tender_regimes)
    assert "updates = []" in source or "updates=[]" in source
    assert "updates.append" in source
    # Ensure the old per-row UPDATE pattern is gone
    assert '                    {"regime": regime, "id": row.id},' not in source
    assert '                )\n                updated += 1' not in source


def test_import_per_agency_experience_uses_batch_update():
    """import_per_agency_experience should batch agency_code updates."""
    from app.services.intelligence.domain.services.dashboard_service import DashboardService

    source = inspect.getsource(DashboardService.import_per_agency_experience)
    assert "updates" in source
    assert "updates.setdefault" in source or "updates.append" in source
    assert source.count('await self.db.execute(') <= 3  # SELECT + potential batch UPDATE + flush


def test_intelligence_data_service_is_deprecated():
    """IntelligenceDataService should carry a deprecation warning."""
    from app.services.intelligence_data_service import IntelligenceDataService

    source = inspect.getsource(IntelligenceDataService.__init__)
    assert "warnings.warn" in source
    assert "deprecated" in source.lower()


def test_crawler_uses_facade():
    """ComprehensiveEGPCrawler should import from facade, not monolith."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "crawler",
        r"D:\A1\procurementflow_final_v3\procurementflow\backend\app\crawlers\comprehensive_egp_crawler.py"
    )
    if spec is None or spec.loader is None:
        pytest.skip("Crawler file not found")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ModuleNotFoundError, ImportError):
        pytest.skip("Crawler dependencies not available in test environment")
    source = inspect.getsource(module.ComprehensiveEGPCrawler)
    assert "IntelligenceDataServiceFacade" in source
    assert "IntelligenceDataService" not in source or "IntelligenceDataServiceFacade" in source


def test_crawler_lazy_loads_facade_with_db():
    """Crawler should lazy-load the facade with a DB session."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "crawler",
        r"D:\A1\procurementflow_final_v3\procurementflow\backend\app\crawlers\comprehensive_egp_crawler.py"
    )
    if spec is None or spec.loader is None:
        pytest.skip("Crawler file not found")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ModuleNotFoundError, ImportError):
        pytest.skip("Crawler dependencies not available in test environment")
    source = inspect.getsource(module.ComprehensiveEGPCrawler)
    assert "_get_intelligence_service" in source
    assert "IntelligenceDataServiceFacade" in source
