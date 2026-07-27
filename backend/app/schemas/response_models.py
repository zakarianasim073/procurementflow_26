"""
Centralized API response models — typed envelopes for every endpoint.

Usage in routers:
    from app.schemas.response_models import SuccessResponse, PaginatedResponse, ...

    @router.get("/items", response_model=PaginatedResponse[ItemRead])
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Generic envelopes
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    """Default success envelope used by most endpoints."""
    success: bool = True
    message: Optional[str] = None


class SuccessWithData(BaseModel):
    """Success with an arbitrary data payload."""
    success: bool = True
    data: Any = None
    message: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    success: bool = True
    total: int = 0
    skip: int = 0
    limit: int = 50
    data: List[T] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard error body (matches FastAPI's HTTPException.detail shape)."""
    detail: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserPayload(BaseModel):
    id: str
    email: str
    plan: str
    tenant_id: Optional[str] = None
    role: str = "viewer"
    name: Optional[str] = None


class AuthTokenResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserPayload] = None


class RefreshTokenResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    success: bool = True


class MeResponse(BaseModel):
    success: bool = True
    user: UserPayload


class ChangePasswordResponse(BaseModel):
    success: bool = True
    message: str = "Password changed successfully"


# ---------------------------------------------------------------------------
# BOQ
# ---------------------------------------------------------------------------

class BOQUploadResponse(BaseModel):
    success: bool = True
    file_id: str
    filename: Optional[str] = None
    file_type: Optional[str] = None
    size_bytes: int = 0
    object_key: Optional[str] = None


class BOQJobResponse(BaseModel):
    job_id: str
    status: str
    status_url: Optional[str] = None


class BOQItemRow(BaseModel):
    item_no: Optional[str] = ""
    code: Optional[str] = ""
    agency: Optional[str] = ""
    work_type: Optional[str] = ""
    desc: Optional[str] = ""
    unit: Optional[str] = ""
    qty: Optional[float] = None
    rate: Optional[float] = None
    sor_rate: Optional[float] = None
    sor_source: Optional[str] = None
    diff: Optional[float] = None
    pct_diff: Optional[float] = None
    flag: Optional[str] = ""
    section: Optional[str] = ""


class BOQSummary(BaseModel):
    by_work_type: List[Any] = Field(default_factory=list)
    total_sor: float = 0.0
    total_quoted: float = 0.0
    discount_pct: float = 0.0


class BOQLatestResponse(BaseModel):
    success: bool = True
    comparison_id: Optional[str] = None
    boq_file_id: Optional[str] = None
    sor_agency: Optional[str] = None
    zone: Optional[str] = None
    items: List[BOQItemRow] = Field(default_factory=list)
    summary: BOQSummary = Field(default_factory=BOQSummary)
    flagged: List[Any] = Field(default_factory=list)
    total_items: Optional[int] = None
    mismatches: Optional[int] = None
    variances: Optional[int] = None
    matches: Optional[int] = None
    below_sor: Optional[int] = None
    excel_path: Optional[str] = None
    docx_path: Optional[str] = None
    tenderai_dir: Optional[str] = None
    created_at: Optional[str] = None
    financial_check: List[Any] = Field(default_factory=list)
    estimated_cost_app: Optional[float] = None


# ---------------------------------------------------------------------------
# SOR
# ---------------------------------------------------------------------------

class SORAgencyInfo(BaseModel):
    id: str
    name: str
    total_rates: int = 0
    has_csv: bool = False


class SORAgenciesResponse(BaseModel):
    agencies: List[SORAgencyInfo] = Field(default_factory=list)


class SORRateLookup(BaseModel):
    code: str
    description: Optional[str] = None
    unit: Optional[str] = None
    zone_a: Optional[float] = None
    zone_b: Optional[float] = None
    zone_c: Optional[float] = None
    zone_d: Optional[float] = None
    rate: Optional[float] = None
    zone: str = "A"
    agency: str = "BWDB"


class SORLoadPdfResponse(BaseModel):
    success: bool = True
    loaded: int = 0
    agency: str


class SORBatchResultItem(BaseModel):
    code: str
    matched: bool = False
    rate: Optional[float] = None
    matched_code: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    agency: Optional[str] = None
    zone: Optional[str] = None


class SORBatchResponse(BaseModel):
    results: List[SORBatchResultItem] = Field(default_factory=list)
    total: int = 0
    matched: int = 0


class SORReimportResponse(BaseModel):
    success: bool = True
    result: Any = None


class SORStatsResponse(BaseModel):
    success: bool = True
    agencies: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Competitors
# ---------------------------------------------------------------------------

class CompetitorCategoryStat(BaseModel):
    category: Optional[str] = None
    count: int = 0
    total_amount: float = 0.0


class CompetitorDistrictStat(BaseModel):
    district: Optional[str] = None
    count: int = 0
    total_amount: float = 0.0


class CompetitorStatsResponse(BaseModel):
    success: bool = True
    total_competitors: int = 0
    total_awarded_amount: float = 0.0
    source: Optional[str] = None
    by_category: List[CompetitorCategoryStat] = Field(default_factory=list)
    by_district: List[CompetitorDistrictStat] = Field(default_factory=list)


class CompetitorAwardItem(BaseModel):
    id: Optional[str] = None
    tender_id: Optional[str] = None
    package_no: Optional[str] = None
    title: Optional[str] = None
    contractor_name: Optional[str] = None
    amount_bdt: Optional[float] = None
    estimated_amount_bdt: Optional[float] = None
    award_date: Optional[str] = None
    agency_code: Optional[str] = None
    district: Optional[str] = None
    procuring_entity: Optional[str] = None


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

class PricingEstimateItem(BaseModel):
    code: Optional[str] = ""
    description: Optional[str] = ""
    unit: Optional[str] = ""
    quantity: float = 0.0
    agency: Optional[str] = None
    zone: Optional[str] = None
    rate: Optional[float] = None
    amount: float = 0.0
    sor_code: Optional[str] = None
    sor_description: Optional[str] = None
    confidence: float = 0.0
    matched: bool = False


class PricingEstimateResponse(BaseModel):
    success: bool = True
    items: List[PricingEstimateItem] = Field(default_factory=list)
    total_items: int = 0
    matched_items: int = 0
    unmatched_items: int = 0
    estimated_total: float = 0.0
    source: str = "sor_service_csv_indexed"


# ---------------------------------------------------------------------------
# Contractors
# ---------------------------------------------------------------------------

class ContractorCapacityResponse(BaseModel):
    success: bool = True
    contractor: Optional[str] = None
    canonical_contractor_id: Optional[str] = None
    total_contracts: int = 0
    total_amount_bdt: float = 0.0
    last_5yr_awarded_amount_bdt: float = 0.0
    work_in_hand_bdt: float = 0.0
    estimated_turnover_bdt: float = 0.0
    avg_award_bdt: float = 0.0
    tender_capacity_bdt: float = 0.0
    tender_value_bdt: float = 0.0
    utilization_ratio: float = 0.0
    capacity_status: str = "unknown"
    agencies_worked: List[Any] = Field(default_factory=list)
    districts_worked: List[Any] = Field(default_factory=list)
    work_type_mix: Dict[str, Any] = Field(default_factory=dict)
    is_joint_venture: bool = False
    jv_member_count: int = 0
    data_confidence_score: float = 0.0
    source: Optional[str] = None


class LiquidityBand(BaseModel):
    low: float = 0.0
    high: float = 0.0


class ContractorFinanceResponse(BaseModel):
    success: bool = True
    contractor: Optional[str] = None
    canonical_contractor_id: Optional[str] = None
    total_contracts: int = 0
    total_amount_bdt: float = 0.0
    last_5yr_awarded_amount_bdt: float = 0.0
    work_in_hand_bdt: float = 0.0
    estimated_turnover_bdt: float = 0.0
    tender_capacity_bdt: float = 0.0
    avg_award_bdt: float = 0.0
    avg_npp: float = 0.0
    avg_discount_pct: float = 0.0
    win_rate: float = 0.0
    total_bids: int = 0
    health_score: float = 0.0
    reliability_score: float = 0.0
    data_confidence_score: float = 0.0
    completion_rate: float = 0.0
    on_time_rate: float = 0.0
    avg_delay_days: float = 0.0
    estimated_liquidity_band_bdt: LiquidityBand = Field(default_factory=LiquidityBand)
    work_type_mix: Dict[str, Any] = Field(default_factory=dict)
    is_joint_venture: bool = False
    jv_member_count: int = 0
    source: Optional[str] = None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchResponse(BaseModel):
    success: bool = True
    query: str = ""
    entity_type: str = ""
    limit: int = 50
    offset: int = 0
    has_more: bool = False
    next_offset: Optional[int] = None
    data: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class GlobalSearchResponse(BaseModel):
    success: bool = True
    query: str = ""
    tenders: List[Dict[str, Any]] = Field(default_factory=list)
    awards: List[Dict[str, Any]] = Field(default_factory=list)
    contractors: List[Dict[str, Any]] = Field(default_factory=list)
    counts: Dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationFinding(BaseModel):
    severity: str
    code: str
    item_no: Optional[str] = None
    document: Optional[str] = None
    message: Optional[str] = None


class ComplianceRule(BaseModel):
    rule_id: str
    rule_code: str
    title: str
    description: str
    category: str
    status: str = "pending"
    details: Optional[str] = None
    version: str = "1.0"
    updated_at: str = ""


class ComplianceCheck(BaseModel):
    check_id: str
    tender_id: str
    rules: List[ComplianceRule] = Field(default_factory=list)
    overall_status: str = "partial"
    score: float = 0.0
    checked_at: str = ""


class ValidationCheckResponse(BaseModel):
    success: bool = True
    tender_id: Optional[str] = None
    compliant: bool = True
    findings: List[ValidationFinding] = Field(default_factory=list)
    source: str = "rule_engine"
    persisted: bool = False


class TenderValidationResponse(BaseModel):
    success: bool = True
    tender_id: Optional[str] = None
    items_checked: int = 0
    compliant: bool = True
    findings: List[ValidationFinding] = Field(default_factory=list)
    source: str = "boq_items"
    persisted: bool = False


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class ReportGenerateResponse(BaseModel):
    success: bool = True
    job_id: str
    status: str = "queued"
    poll_url: Optional[str] = None


class ReportJobStatusResponse(BaseModel):
    success: bool = True
    job_id: Optional[str] = None
    status: Optional[str] = None
    report_type: Optional[str] = None
    tender_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# System / Admin
# ---------------------------------------------------------------------------

class AdminActionResult(BaseModel):
    success: bool = True
    message: Optional[str] = None
    rows_affected: Optional[int] = None
    job_id: Optional[str] = None
    status: Optional[str] = None
    duration_seconds: Optional[float] = None


class SLTDashboardResponse(BaseModel):
    success: bool = True
    slt: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------

class MonitorConfigResponse(BaseModel):
    enabled: Optional[bool] = None
    scan_interval_minutes: Optional[int] = None
    targets: List[Any] = Field(default_factory=list)
    alerts: List[Any] = Field(default_factory=list)


class MonitorConfigUpdateResponse(BaseModel):
    success: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class MonitorToggleResponse(BaseModel):
    success: bool = True
    enabled: Optional[bool] = None


class MonitorAlertsResponse(BaseModel):
    success: bool = True
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# Government Portals
# ---------------------------------------------------------------------------

class GovernmentPortalResponse(BaseModel):
    success: bool = True
    source: Optional[str] = None
    last_updated: Optional[str] = None
    count: int = 0
    data: List[Any] = Field(default_factory=list)


class PortalOrganization(BaseModel):
    id: str
    name: str
    type: str
    division: Optional[str] = None
    zone: Optional[str] = None


class PortalOrganizationsResponse(BaseModel):
    success: bool = True
    source: Optional[str] = None
    count: int = 0
    data: List[PortalOrganization] = Field(default_factory=list)


class PortalZone(BaseModel):
    code: str
    name: str
    agency: str
    divisions: List[str] = Field(default_factory=list)
    districts: List[str] = Field(default_factory=list)
    agencies: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class PortalZonesResponse(BaseModel):
    success: bool = True
    source: Optional[str] = None
    count: int = 0
    data: List[PortalZone] = Field(default_factory=list)


class PortalHealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: Optional[str] = None
    government_portal_apis: Dict[str, str] = Field(default_factory=dict)
    total_sources: int = 0
    data_records: int = 0


# ---------------------------------------------------------------------------
# Rate Analysis
# ---------------------------------------------------------------------------

class RateAnalysisComparison(BaseModel):
    total_items: int = 0
    total_sor: float = 0.0
    total_quoted: float = 0.0
    discount_pct: float = 0.0
    flagged_items: int = 0


class RateAnalysisProfitMargins(BaseModel):
    avg_pct: Optional[float] = None
    min_pct: Optional[float] = None
    max_pct: Optional[float] = None
    safe_gt_15: int = 0
    tight_5_to_15: int = 0
    at_risk_0_to_5: int = 0
    loss_le_0: int = 0


class RateAnalysisResponse(BaseModel):
    success: bool = True
    tender_id: Optional[str] = None
    zone: str = "A"
    comparison: RateAnalysisComparison = Field(default_factory=RateAnalysisComparison)
    rate_analysis: Dict[str, Any] = Field(default_factory=dict)
    excel_path: Optional[str] = None
    details: List[Dict[str, Any]] = Field(default_factory=list)


class AnalyzeItemsResponse(BaseModel):
    success: bool = True
    zone: str = "A"
    items_analyzed: int = 0
    results: List[Dict[str, Any]] = Field(default_factory=list)


class MarketPricesResponse(BaseModel):
    success: bool = True
    zone: str = "A"
    last_updated: Optional[str] = None
    source: Optional[str] = None
    materials: Dict[str, Any] = Field(default_factory=dict)
    labor: Dict[str, Any] = Field(default_factory=dict)
    equipment: Dict[str, Any] = Field(default_factory=dict)
    indices: Dict[str, Any] = Field(default_factory=dict)


class CompositionSummary(BaseModel):
    sor_code: str
    elements: int = 0
    materials: int = 0
    labor: int = 0
    equipment: int = 0


class CompositionsResponse(BaseModel):
    success: bool = True
    count: int = 0
    compositions: List[CompositionSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Canonical
# ---------------------------------------------------------------------------

class CanonicalStatusResponse(BaseModel):
    success: bool = True
    requested_by: Dict[str, Any] = Field(default_factory=dict)
    tables: Dict[str, int] = Field(default_factory=dict)
    amount_quality: Dict[str, Any] = Field(default_factory=dict)
    contractor_quality: Dict[str, Any] = Field(default_factory=dict)
    top_capacity_contractors: List[Dict[str, Any]] = Field(default_factory=list)


class RepairQueueSummaryItem(BaseModel):
    issue_type: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    count: int = 0


class RepairQueueSummaryResponse(BaseModel):
    success: bool = True
    summary: List[RepairQueueSummaryItem] = Field(default_factory=list)


class RepairQueueRecord(BaseModel):
    repair_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_key: Optional[str] = None
    source_table: Optional[str] = None
    source_id: Optional[str] = None
    issue_type: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    suggested_action: Optional[str] = None
    evidence: Optional[Any] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RepairQueueResponse(BaseModel):
    success: bool = True
    total: int = 0
    limit: int = 100
    offset: int = 0
    records: List[RepairQueueRecord] = Field(default_factory=list)


class RepairResolveResponse(BaseModel):
    success: bool = True
    record: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------

class CrawlStartResponse(BaseModel):
    run_id: str
    status: str = "started"
    type: str


class CrawlStatusResponse(BaseModel):
    run_id: str
    status: str
    type: Optional[str] = None
    stats: Dict[str, Any] = Field(default_factory=dict)


class CrawlerInfo(BaseModel):
    name: str
    type: str
    description: Optional[str] = None


class CrawlerListResponse(BaseModel):
    crawlers: List[CrawlerInfo] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Brain Router
# ---------------------------------------------------------------------------

class BrainUIResponse(BaseModel):
    success: bool = True
    feature: Optional[str] = None
    action: Optional[str] = None


class AgentResultResponse(BaseModel):
    agent_id: str
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


class BrainRunResponse(BaseModel):
    success: bool = True
    run_id: Optional[str] = None
    pipeline: Optional[str] = None
    results: List[AgentResultResponse] = Field(default_factory=list)
    error: Optional[str] = None


class KnowledgeEntryResponse(BaseModel):
    id: Optional[str] = None
    entry_type: Optional[str] = None
    tender_id: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None


class KnowledgeSearchResponse(BaseModel):
    success: bool = True
    query: Optional[str] = None
    results: List[KnowledgeEntryResponse] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# Intelligence Gap (Contractor sub-routes)
# ---------------------------------------------------------------------------

class ContractorExperienceItem(BaseModel):
    category: str = "Unknown"
    projects_count: int = 0
    avg_value: float = 0.0
    largest_value: float = 0.0
    years_active: int = 1
    trend: str = "stable"


class ContractorAwardsPage(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    awards: List[Dict[str, Any]] = Field(default_factory=list)


class EligibilityRule(BaseModel):
    rule_id: str
    rule_title: str
    status: str = "gap"
    evidence: Optional[str] = None


class ContractorRiskResponse(BaseModel):
    compliance: str = "medium"
    market: str = "medium"
    financial: str = "medium"
    operational: str = "medium"
    overall: str = "medium"
    flags: List[str] = Field(default_factory=list)


class ContractorOpportunityItem(BaseModel):
    tender_id: Optional[str] = None
    match_score: float = 0.0
    reason: Optional[str] = None
    partner_recommendation: Optional[str] = None


# ---------------------------------------------------------------------------
# Intelligence Gap - Frontend-matched types (match ContractorProfile sub-types)
# ---------------------------------------------------------------------------

class ContractorExperienceCategory(BaseModel):
    category: str
    projects_count: int
    avg_value: float
    largest_value: float
    years_active: int
    trend: str


class ContractorExperienceResponse(BaseModel):
    total_years: int = 0
    by_category: List[ContractorExperienceCategory] = Field(default_factory=list)


class ContractorEligibilityResponse(BaseModel):
    rule_37_experience: str = "gap"
    rule_38_financial: str = "gap"
    rule_40_technical: str = "gap"
    missing_categories: Optional[List[str]] = None


class RiskFlag(BaseModel):
    flag: str
    severity: str
    recommendation: str


class ContractorRiskProfileResponse(BaseModel):
    compliance_risk: str = "medium"
    market_risk: str = "medium"
    financial_risk: str = "medium"
    operational_risk: str = "medium"
    overall_risk: str = "medium"
    flags: List[RiskFlag] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatModelsResponse(BaseModel):
    success: bool = True
    models: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardStatsResponse(BaseModel):
    success: bool = True
    stats: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Awards (extra list response for raw dict returns)
# ---------------------------------------------------------------------------

class AwardListItem(BaseModel):
    id: Optional[str] = None
    source_id: Optional[str] = None
    tender_id: Optional[str] = None
    title: Optional[str] = None
    procuring_entity: Optional[str] = None
    contractor_name: Optional[str] = None
    amount_bdt: Optional[float] = None
    award_date: Optional[str] = None
    agency_code: Optional[str] = None
    district: Optional[str] = None


# ---------------------------------------------------------------------------
# Tenders (extra list response for raw dict returns)
# ---------------------------------------------------------------------------

class TenderListItem(BaseModel):
    id: Optional[str] = None
    tender_id: Optional[str] = None
    package_no: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    agency_code: Optional[str] = None
    estimated_amount_bdt: Optional[float] = None
    closing_date: Optional[str] = None
    status: Optional[str] = None
    division: Optional[str] = None
    district: Optional[str] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Extra schemas for endpoints returning Dict[str, Any] directly
# ---------------------------------------------------------------------------

class MonitorScanResponse(BaseModel):
    success: bool = True
    results: Any = None


class MonitorStatsResponse(BaseModel):
    success: bool = True
    tender_count: int = 0
    entity_count: int = 0
    scanned: int = 0
    alerts: int = 0


class SimpleSuccessResponse(BaseModel):
    success: bool = True


class TargetAgencyResponse(BaseModel):
    id: str
    name: str
    office_count: int
    total_packages: int


class TargetAgenciesResponse(BaseModel):
    agencies: Dict[str, TargetAgencyResponse]


class FullTreeTargets(BaseModel):
    name: str
    office_count: int


class FullTreeResponse(BaseModel):
    tree: List[Dict[str, Any]]
    total: int
    targets: Dict[str, FullTreeTargets]
    total_packages: int


class MinistryResponse(BaseModel):
    id: str
    name: str
    type: str
    office_count: int
    total_packages: int


class MinistryListResponse(BaseModel):
    success: bool = True
    ministries: List[MinistryResponse]


class OfficeResponse(BaseModel):
    id: str
    name: str
    type: str
    ministry: Optional[str] = None
    package_count: Optional[int] = None
    match_field: Optional[str] = None


class SearchResultResponse(BaseModel):
    id: str
    name: str
    type: str
    ministry: Optional[str] = None
    package_count: Optional[int] = None
    match_field: Optional[str] = None
    
    class Config:
        extra = "allow"


class SearchDeptreeResponse(BaseModel):
    results: List[SearchResultResponse]
    total: int


class SearchLiveTendersResponse(BaseModel):
    view_type: str
    
    class Config:
        extra = "allow"
