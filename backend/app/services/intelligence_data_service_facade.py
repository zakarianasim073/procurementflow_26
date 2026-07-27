"""Facade layer that wraps the 6 domain services behind the old IntelligenceDataService interface.

This allows routers to keep using IntelligenceDataService while methods are migrated
to domain-specific services. Deprecated methods will route to new services.
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

from app.services.intelligence.domain.services import (
    DiscoveryService,
    TenderService,
    AwardService,
    ContractorService,
    CompetitorService,
    DashboardService,
)
from app.services.intelligence.domain.services.service_registry import get_service


class IntelligenceDataServiceFacade:
    """Thin facade that delegates to domain-specific services.

    Maintains backward compatibility for all existing router code.
    Methods not yet migrated are delegated to the original monolith.
    """

    def __init__(self, db):
        self.db = db
        # Lazy-loaded services — only instantiate when needed
        self._discovery: Optional[DiscoveryService] = None
        self._tender: Optional[TenderService] = None
        self._award: Optional[AwardService] = None
        self._contractor: Optional[ContractorService] = None
        self._competitor: Optional[CompetitorService] = None
        self._dashboard: Optional[DashboardService] = None

    # ── Lazy property accessors ─────────────────────────────────────────

    @property
    def discovery(self) -> DiscoveryService:
        if self._discovery is None:
            self._discovery = DiscoveryService(self.db)
        return self._discovery

    @property
    def tender(self) -> TenderService:
        if self._tender is None:
            self._tender = TenderService(self.db)
        return self._tender

    @property
    def award(self) -> AwardService:
        if self._award is None:
            self._award = AwardService(self.db)
        return self._award

    @property
    def contractor(self) -> ContractorService:
        if self._contractor is None:
            self._contractor = ContractorService(self.db)
        return self._contractor

    @property
    def competitor(self) -> CompetitorService:
        if self._competitor is None:
            self._competitor = CompetitorService(self.db)
        return self._competitor

    @property
    def dashboard(self) -> DashboardService:
        if self._dashboard is None:
            self._dashboard = DashboardService(self.db)
        return self._dashboard

    @property
    def domain_services(self) -> Dict[str, Any]:
        """Compatibility map for diagnostics while callers migrate to direct services."""
        return {
            "discovery": self.discovery,
            "tender": self.tender,
            "award": self.award,
            "contractor": self.contractor,
            "competitor": self.competitor,
            "dashboard": self.dashboard,
        }

    # ── Discovery / Import (delegated to DiscoveryService) ───────────────

    async def import_existing_json_data(self, root_dir=None, progress=None):
        warnings.warn("Use discovery.import_existing_json_data()", DeprecationWarning, stacklevel=2)
        return await self.discovery.import_existing_json_data(progress=progress)

    async def ingest_app_plan_record(self, record, progress=None):
        warnings.warn("Use discovery.ingest_app_plan_record()", DeprecationWarning, stacklevel=2)
        return await self.discovery.ingest_app_plan_record(record)

    async def ingest_live_tender_notice(self, tender_info, source_type="egp_live_scan"):
        warnings.warn("Use discovery.ingest_live_tender_notice()", DeprecationWarning, stacklevel=2)
        return await self.discovery.ingest_live_tender_notice(tender_info, source_type)

    async def ingest_noa_award_notice(self, award_info, progress=None):
        warnings.warn("Use award.ingest_noa_award_notice()", DeprecationWarning, stacklevel=2)
        return await self.award.ingest_noa_award_notice(award_info)

    async def backfill_live_tender_shell_records(self, progress=None):
        warnings.warn("Use discovery.backfill_live_tender_shell_records()", DeprecationWarning, stacklevel=2)
        return await self.discovery.backfill_live_tender_shell_records()

    async def reconcile_eexperience_to_tender(self, progress=None):
        warnings.warn("Use discovery.reconcile_eexperience_to_tender()", DeprecationWarning, stacklevel=2)
        return await self.discovery.reconcile_eexperience_to_tender()

    async def reconcile_awards_to_app_records(self, progress=None):
        warnings.warn("Use discovery.reconcile_awards_to_app_records()", DeprecationWarning, stacklevel=2)
        return await self.discovery.reconcile_awards_to_app_records(progress)

    async def reconcile_execution_to_lifecycle(self):
        warnings.warn("Use tender.reconcile_execution_to_lifecycle()", DeprecationWarning, stacklevel=2)
        return await self.tender.reconcile_execution_to_lifecycle()

    async def import_lifecycle_from_json(self, json_path=None, progress=None):
        warnings.warn("Use tender.import_lifecycle_from_json()", DeprecationWarning, stacklevel=2)
        return await self.tender.import_lifecycle_from_json(json_path, progress)

    async def import_matched_lifecycle_from_json(self, matched_path, progress=None):
        warnings.warn("Use tender.import_matched_lifecycle_from_json()", DeprecationWarning, stacklevel=2)
        return await self.tender.import_matched_lifecycle_from_json(matched_path, progress)

    async def import_eexperience_from_json(self, json_path, progress=None):
        warnings.warn("Use dashboard.import_eexperience_from_json()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.import_eexperience_from_json(json_path, progress)

    async def import_experience_to_dedicated_tables(self, json_path=None, progress=None):
        warnings.warn("Use dashboard.import_experience_to_dedicated_tables()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.import_experience_to_dedicated_tables()

    async def import_awards_from_json(self, json_path, progress=None):
        warnings.warn("Use award.import_awards_from_json()", DeprecationWarning, stacklevel=2)
        return await self.award.import_awards_from_json(json_path, progress)

    async def import_live_tenders_from_json(self, json_path, progress=None):
        warnings.warn("Use discovery.import_live_tenders_from_json()", DeprecationWarning, stacklevel=2)
        return await self.discovery.import_live_tenders_from_json(json_path, progress)

    async def import_app_structure_from_json(self, json_path=None, progress=None):
        warnings.warn("Use discovery.import_app_structure_from_json()", DeprecationWarning, stacklevel=2)
        return await self.discovery.import_app_structure_from_json(json_path, progress)

    async def import_contractors_from_json(self, json_path=None, progress=None):
        warnings.warn("Use contractor.import_contractors_from_json()", DeprecationWarning, stacklevel=2)
        return await self.contractor.import_contractors_from_json(json_path, progress)

    async def rebuild_contractor_intelligence(self, progress=None):
        warnings.warn("Use contractor.rebuild_contractor_intelligence()", DeprecationWarning, stacklevel=2)
        return await self.contractor.rebuild_contractor_intelligence()

    async def rebuild_procurement_lifecycle(self, progress=None):
        warnings.warn("Use tender.rebuild_procurement_lifecycle()", DeprecationWarning, stacklevel=2)
        return await self.tender.rebuild_procurement_lifecycle()

    async def rebuild_aggregate_intelligence(self, progress=None):
        warnings.warn("Use dashboard.rebuild_aggregate_intelligence()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.rebuild_aggregate_intelligence()

    async def backfill_tender_regimes(self, progress=None):
        warnings.warn("Use tender.backfill_tender_regimes()", DeprecationWarning, stacklevel=2)
        return await self.tender.backfill_tender_regimes()

    async def reconcile_award_package_mapping_from_json(self, flat_path, progress=None):
        warnings.warn("Use discovery.reconcile_award_package_mapping_from_json()", DeprecationWarning, stacklevel=2)
        return await self.discovery.reconcile_award_package_mapping_from_json(flat_path, progress)

    # ── Search / Query (delegated to TenderService) ──────────────────────

    async def search_live_tenders(self, keyword=None, filters=None, limit=50, **kwargs):
        warnings.warn("Use tender.search_live_tenders()", DeprecationWarning, stacklevel=2)
        return await self.tender.search_live_tenders(
            department_id=kwargs.get("department_id", ""),
            office_id=kwargs.get("office_id", ""),
            keyword=keyword or kwargs.get("keyword", ""),
            page=kwargs.get("page", 1),
            page_size=kwargs.get("page_size", limit),
        )

    async def get_live_tender_stats(self, filters=None, **kwargs):
        warnings.warn("Use dashboard.get_live_tender_stats()", DeprecationWarning, stacklevel=2)
        agency = kwargs.get("agency") or (filters.get("agency") if isinstance(filters, dict) else filters)
        return await self.dashboard.get_live_tender_stats(agency=agency)

    async def query_lifecycle(self, tender_id=None, package_no=None, status=None, **kwargs):
        warnings.warn("Use tender.query_lifecycle()", DeprecationWarning, stacklevel=2)
        filters = dict(kwargs)
        if tender_id:
            filters["tender_id"] = tender_id
        if package_no:
            filters["package_no"] = package_no
        if status:
            filters["match_type"] = status
        return await self.tender.query_lifecycle(**filters)

    async def query_works_records(self, filters=None, limit=50, offset=0, **kwargs):
        warnings.warn("Use tender.query_works_records()", DeprecationWarning, stacklevel=2)
        query = dict(filters or {})
        query.update({key: value for key, value in kwargs.items() if value is not None})
        query.setdefault("limit", limit)
        query.setdefault("offset", offset)
        return await self.tender.query_works_records(**query)

    # ── Contractor (delegated to ContractorService) ─────────────────────

    async def list_contractors(self, filters=None, limit=50, **kwargs):
        warnings.warn("Use contractor.list_contractors()", DeprecationWarning, stacklevel=2)
        offset = kwargs.get("offset")
        if offset is None:
            offset = int((filters or {}).get("offset", 0)) if isinstance(filters, dict) else 0
        return await self.contractor.list_contractors(limit=limit, offset=offset)

    async def search_contractors(self, keyword=None, filters=None, limit=50):
        warnings.warn("Use contractor.search_contractors()", DeprecationWarning, stacklevel=2)
        return await self.contractor.search_contractors(keyword or "", limit=limit)

    async def get_contractor(self, contractor_id, include_history=True):
        warnings.warn("Use contractor.get_contractor()", DeprecationWarning, stacklevel=2)
        return await self.contractor.get_contractor(contractor_id)

    async def get_contractor_stats(self, contractor_id=None):
        warnings.warn("Use contractor.get_contractor_stats()", DeprecationWarning, stacklevel=2)
        return await self.contractor.get_contractor_stats()

    async def get_contractor_dna(self, contractor_id, include_history=True):
        warnings.warn("Use contractor.get_contractor_dna()", DeprecationWarning, stacklevel=2)
        return await self.contractor.get_contractor_dna(contractor_id)

    async def get_contractor_performance(self, contractor_id=None, metric="all", **kwargs):
        warnings.warn("Use contractor.get_contractor_performance()", DeprecationWarning, stacklevel=2)
        name = kwargs.get("contractor_name") or contractor_id
        source = kwargs.get("source")
        return await self.contractor.get_contractor_performance(name, source=source)

    async def benchmark_contractor(self, contractor_id, against=None, **kwargs):
        warnings.warn("Use contractor.benchmark_contractor()", DeprecationWarning, stacklevel=2)
        return await self.contractor.benchmark_contractor(contractor_id, agency=kwargs.get("agency", against))

    # ── Award (delegated to AwardService) ────────────────────────────────

    async def list_awards_for_agent(self, agent_id=None, filters=None, limit=50):
        warnings.warn("Use award.list_awards_for_agent()", DeprecationWarning, stacklevel=2)
        agency = ""
        if isinstance(filters, dict):
            agency = filters.get("agency") or filters.get("agency_code") or ""
        elif isinstance(agent_id, str):
            agency = agent_id
        return await self.award.list_awards_for_agent(agency=agency, limit=limit)

    async def get_award_data_quality_stats(self, filters=None):
        warnings.warn("Use award.get_award_data_quality_stats()", DeprecationWarning, stacklevel=2)
        return await self.award.get_award_data_quality_stats()

    async def get_award_trends(self, agency_code=None, period="monthly"):
        warnings.warn("Use dashboard.get_award_trends()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.get_award_trends(agency_code, period)

    # ── Competitor (delegated to CompetitorService) ──────────────────────

    async def get_agency_intelligence(self, agency_code=None, filters=None):
        warnings.warn("Use competitor.get_agency_intelligence()", DeprecationWarning, stacklevel=2)
        return await self.competitor.get_agency_intelligence(agency_code)

    async def get_zone_intelligence(self, zone_code=None, filters=None):
        warnings.warn("Use competitor.get_zone_intelligence()", DeprecationWarning, stacklevel=2)
        return await self.competitor.get_zone_intelligence()

    async def get_discount_patterns(self, agency_code=None, period="monthly", **kwargs):
        warnings.warn("Use competitor.get_discount_patterns()", DeprecationWarning, stacklevel=2)
        agency = kwargs.get("agency", agency_code)
        zone = kwargs.get("zone")
        return await self.competitor.get_discount_patterns(agency=agency, zone=zone)

    async def get_npp_trends(self, agency_code=None, period="monthly", **kwargs):
        warnings.warn("Use competitor.get_npp_trends()", DeprecationWarning, stacklevel=2)
        months = kwargs.get("months")
        if months is None and isinstance(agency_code, int):
            months = agency_code
        return await self.competitor.get_npp_trends(months=months or 12)

    # ── Dashboard (delegated to DashboardService) ───────────────────────

    async def get_lifecycle_stats(self, filters=None):
        warnings.warn("Use dashboard.get_lifecycle_stats()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.get_lifecycle_stats()

    async def get_eexperience_stats(self, filters=None, limit=50, **kwargs):
        warnings.warn("Use dashboard.get_eexperience_stats()", DeprecationWarning, stacklevel=2)
        source = kwargs.get("source") or (filters.get("source") if isinstance(filters, dict) else None)
        return await self.dashboard.get_eexperience_stats(source=source)

    async def get_execution_intelligence(self, filters=None, **kwargs):
        warnings.warn("Use dashboard.get_execution_intelligence()", DeprecationWarning, stacklevel=2)
        query = dict(filters or {}) if isinstance(filters, dict) else {}
        query.update(kwargs)
        return await self.dashboard.get_execution_intelligence(**query)

    async def query_completed_executions(self, filters=None, limit=50, **kwargs):
        warnings.warn("Use dashboard.query_completed_executions()", DeprecationWarning, stacklevel=2)
        query = dict(filters or {}) if isinstance(filters, dict) else {}
        query.update(kwargs)
        query.setdefault("limit", limit)
        return await self.dashboard.query_completed_executions(**query)

    async def query_ongoing_executions(self, filters=None, limit=50, **kwargs):
        warnings.warn("Use dashboard.query_ongoing_executions()", DeprecationWarning, stacklevel=2)
        query = dict(filters or {}) if isinstance(filters, dict) else {}
        query.update(kwargs)
        query.setdefault("limit", limit)
        return await self.dashboard.query_ongoing_executions(**query)

    async def get_rate_quoted_analysis(self, filters=None, limit=50, **kwargs):
        warnings.warn("Use dashboard.get_rate_quoted_analysis()", DeprecationWarning, stacklevel=2)
        query = dict(filters or {}) if isinstance(filters, dict) else {}
        query.update(kwargs)
        query.setdefault("limit", limit)
        return await self.dashboard.get_rate_quoted_analysis(**query)

    async def query_eexperience(self, filters=None, limit=50, offset=0, **kwargs):
        warnings.warn("Use dashboard.query_eexperience()", DeprecationWarning, stacklevel=2)
        query = dict(filters or {}) if isinstance(filters, dict) else {}
        query.update(kwargs)
        query.setdefault("limit", limit)
        query.setdefault("offset", offset)
        return await self.dashboard.query_eexperience(**query)

    async def get_import_counts(self, filters=None):
        warnings.warn("Use dashboard.get_import_counts()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.get_import_counts()

    async def get_executive_overview(self, filters=None):
        warnings.warn("Use dashboard.get_executive_overview()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.get_executive_overview()

    async def get_agent_feed(self, agent_id=None, limit=50, **kwargs):
        warnings.warn("Use dashboard.get_agent_feed()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.get_agent_feed(agency=kwargs.get("agency", agent_id), limit=limit)

    async def get_department_tree(self, agency_code=None):
        warnings.warn("Use dashboard.get_department_tree()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.get_department_tree()

    async def get_eexperience_timeline(self, agency_code=None, period="monthly", **kwargs):
        warnings.warn("Use dashboard.get_eexperience_timeline()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.get_eexperience_timeline(
            source=kwargs.get("source"),
            granularity=kwargs.get("granularity", "month"),
            year=kwargs.get("year"),
        )

    async def get_agency_comparison(self, agency_codes=None, metric="awards", **kwargs):
        warnings.warn("Use dashboard.get_agency_comparison()", DeprecationWarning, stacklevel=2)
        source = kwargs.get("source") or (agency_codes if isinstance(agency_codes, str) else None)
        return await self.dashboard.get_agency_comparison(source=source)

    async def list_eexperience_agencies(self, limit=50, **kwargs):
        warnings.warn("Use dashboard.list_eexperience_agencies()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.list_eexperience_agencies(source=kwargs.get("source"))

    async def import_per_agency_experience(self, agency_code, json_path, progress=None):
        warnings.warn("Use dashboard.import_per_agency_experience()", DeprecationWarning, stacklevel=2)
        return await self.dashboard.import_per_agency_experience()

    # ── Crawler-specific legacy methods (delegated to domain services) ─────

    async def store_opening_report(self, opening_report: Dict[str, Any]) -> Dict[str, Any]:
        """Store an opening report. Delegates to tender service."""
        from app.models.intelligence import OpeningReport
        from sqlalchemy import select

        if not opening_report or not opening_report.get("tender_id"):
            return {"status": "skipped", "reason": "missing_tender_id"}

        tender_id = opening_report.get("tender_id")
        stmt = select(OpeningReport).where(OpeningReport.tender_id == tender_id)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return {"status": "existing", "tender_id": tender_id}

        report = OpeningReport(
            id=self._uuid(),
            tender_id=tender_id,
            package_no=opening_report.get("package_no", ""),
            opening_date=opening_report.get("opening_date"),
            bidder_count=opening_report.get("bidder_count", 0),
            responsive_bidders=opening_report.get("responsive_bidders", 0),
            award_winner=opening_report.get("award_winner"),
            award_amount=opening_report.get("award_amount"),
            raw_data=opening_report,
            source_url=opening_report.get("source_url", ""),
        )
        self.db.add(report)
        await self.db.flush()
        return {"status": "stored", "tender_id": tender_id}

    async def collect_comprehensive_awards_data(self) -> List[Dict[str, Any]]:
        """Collect all award data. Delegates to award service."""
        return await self.award.list_awards_for_agent(agency="", limit=10000)

    async def store_award_record(self, award: Dict[str, Any]) -> Dict[str, Any]:
        """Store a single award record. Delegates to discovery service."""
        return await self.discovery.ingest_noa_award_notice(award)

    async def store_contract_record(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Store a contract record. Contracts are tracked inside lifecycle."""
        return {"status": "noop", "reason": "contracts_tracked_in_lifecycle"}

    async def get_all_contractors_from_awards(self) -> List[Dict[str, Any]]:
        """Get all contractors from awards. Delegates to contractor service."""
        return await self.contractor.list_contractors(limit=10000, offset=0)

    async def collect_contractor_experience(self, contractor: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect experience for a contractor. Delegates to contractor service."""
        contractor_name = contractor.get("contractor_name") or contractor.get("name")
        if not contractor_name:
            return []
        perf = await self.contractor.get_contractor_performance(contractor_name=contractor_name)
        return perf.get("records", []) if isinstance(perf, dict) else []

    async def store_experience_record(self, exp_record: Dict[str, Any]) -> Dict[str, Any]:
        """Store a single experience record. Delegates to discovery service."""
        return await self.discovery.import_eexperience_from_json(exp_record)

    async def import_all_awards_to_database(self) -> Dict[str, Any]:
        """Bulk import all awards. Delegates to award service."""
        return await self.award.rebuild_award_intelligence()

    async def import_all_contracts_to_database(self) -> Dict[str, Any]:
        """Bulk import all contracts. Contracts are tracked in lifecycle."""
        return {"status": "noop", "imported": 0, "reason": "contracts_tracked_in_lifecycle"}

    async def import_all_experience_to_database(self) -> Dict[str, Any]:
        """Bulk import all experience records. Delegates to dashboard service."""
        return await self.dashboard.import_experience_to_dedicated_tables()

    async def generate_contractor_dna_profiles(self) -> Dict[str, Any]:
        """Generate contractor DNA profiles. Delegates to contractor service."""
        return await self.contractor.rebuild_contractor_intelligence()

    def _uuid(self) -> str:
        import uuid
        return str(uuid.uuid4())

    # ── Direct access to domain services (for new code) ─────────────────

    @property
    def discovery_service(self) -> DiscoveryService:
        return self.discovery

    @property
    def tender_service(self) -> TenderService:
        return self.tender

    @property
    def award_service(self) -> AwardService:
        return self.award

    @property
    def contractor_service(self) -> ContractorService:
        return self.contractor

    @property
    def competitor_service(self) -> CompetitorService:
        return self.competitor

    @property
    def dashboard_service(self) -> DashboardService:
        return self.dashboard
