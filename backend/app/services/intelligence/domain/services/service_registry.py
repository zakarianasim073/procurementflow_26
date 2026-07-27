"""Service registry mapping names to domain service classes."""

from .discovery_service import DiscoveryService
from .tender_service import TenderService
from .award_service import AwardService
from .contractor_service import ContractorService
from .competitor_service import CompetitorService
from .dashboard_service import DashboardService
from .rate_analysis_service import RateAnalysisService

SERVICE_REGISTRY: dict[str, type] = {
    "discovery": DiscoveryService,
    "tender": TenderService,
    "award": AwardService,
    "contractor": ContractorService,
    "competitor": CompetitorService,
    "dashboard": DashboardService,
    "rate_analysis": RateAnalysisService,
}


def get_service(name: str):
    """Return the service class for the given name."""
    return SERVICE_REGISTRY.get(name)
