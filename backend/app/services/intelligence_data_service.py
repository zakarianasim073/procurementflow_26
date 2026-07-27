"""
PostgreSQL-backed intelligence service — DEPRECATED.

This module is retained only for backward compatibility.
All new code should import from:
  - ``app.services.intelligence_data_service_facade.IntelligenceDataServiceFacade``
  - Domain services directly: ``app.services.intelligence.domain.services.*``

The ``IntelligenceDataService`` class below inherits from ``IntelligenceDataServiceFacade``
so every existing import continues to work unchanged.
"""
from __future__ import annotations

import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.intelligence_data_service_facade import IntelligenceDataServiceFacade

# ---------------------------------------------------------------------------
# Data-classes & constants — kept here for import compatibility
# ---------------------------------------------------------------------------

UTC = timezone.utc


@dataclass
class ImportProgress:
    """Mutable progress tracker shared between the service and the status endpoint."""
    state: str = "queued"
    started: bool = False
    current_phase: str = "waiting"
    current_file: str = ""
    files_completed: int = 0
    files_total: int = 0
    current_file_records: int = 0
    current_file_imported: int = 0
    records_committed: int = 0
    records: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    summary: Optional[Dict[str, int]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        pct = (self.files_completed / self.files_total * 100) if self.files_total > 0 else 0
        return {
            "state": self.state,
            "started": self.started,
            "current_phase": self.current_phase,
            "current_file": self.current_file,
            "files_completed": self.files_completed,
            "files_total": self.files_total,
            "progress_pct": round(pct, 1),
            "current_file_records": self.current_file_records,
            "current_file_imported": self.current_file_imported,
            "records_committed": self.records_committed,
            "records": dict(self.records),
            "summary": self.summary,
            "error": self.error,
        }


RUNTIME_DIR = Path(__file__).resolve().parent.parent.parent / "runtime"
LEGACY_ROOTS = [
    RUNTIME_DIR / "data_intel",
    RUNTIME_DIR / "knowledge",
    Path(__file__).resolve().parent.parent.parent / "crawl_output",
    Path(__file__).resolve().parent.parent.parent.parent / "data",
]

# Map of deprecated method → replacement service + method for diagnostics
_DEPRECATION_MAP: dict[str, str] = {}


class IntelligenceDataService(IntelligenceDataServiceFacade):
    """Backward-compatible subclass of IntelligenceDataServiceFacade.

    All methods now live on the facade or one of its 6 domain services.
    This class adds only a deprecation warning on construction.
    """

    def __init__(self, db):
        super().__init__(db)
        warnings.warn(
            "IntelligenceDataService is deprecated. Use IntelligenceDataServiceFacade or "
            "domain services directly (DiscoveryService, TenderService, AwardService, "
            "ContractorService, CompetitorService, DashboardService).",
            DeprecationWarning,
            stacklevel=2,
        )
