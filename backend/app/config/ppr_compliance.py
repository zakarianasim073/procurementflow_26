"""PPR-2025 Compliance Engine configuration and validation rules."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import re


@dataclass
class NPPIItem:
    code: str
    description: str
    compliant_rate: float
    non_compliant_action: str
    verification_method: str


@dataclass
class SLTRequirements:
    minimum_daily_wages: int = 650
    overtime_multiplier: float = 1.5
    holiday_allowances: List[int] = field(default_factory=lambda: [101, 102, 103, 104, 105])
    safety_equipment: List[str] = field(default_factory=lambda: [
        "Hard hat", "Safety vest", "Work boots", "Gloves", "Safety belt", "First aid kit",
    ])


@dataclass
class CodePatterns:
    bwdb: re.Pattern = field(default_factory=lambda: re.compile(r"^\d{2}-\d{3}-\d{2}$"))
    pwd: re.Pattern = field(default_factory=lambda: re.compile(r"^\d{2}\.\d+"))
    lged: re.Pattern = field(default_factory=lambda: re.compile(r"^[2-9]\.\d{2}"))


@dataclass
class AuditRequirements:
    retention_period_years: int = 3
    mandatory_approvals: List[str] = field(default_factory=lambda: [
        "projectManager", "financeManager", "complianceOfficer",
    ])
    signature_requirements: List[str] = field(default_factory=lambda: [
        "bidderSignature", "reviewerSignature", "approverSignature", "witnessSignature",
    ])


@dataclass
class BillingCompliance:
    required_fields: List[str] = field(default_factory=lambda: [
        "vendorName", "bidNumber", "itemCode", "quantity", "unitRate",
        "totalAmount", "taxRate", "netAmount", "approvalStatus", "verificationCertificate",
    ])
    boq_formats: List[str] = field(default_factory=lambda: ["standard-boq-v1", "enhanced-boq-v2"])
    sod_formats: List[str] = field(default_factory=lambda: ["standard-sod-v1", "detailed-sod-v2"])
    audit: AuditRequirements = field(default_factory=AuditRequirements)


@dataclass
class ZoneCompliance:
    zones: List[str] = field(default_factory=lambda: ["A", "B", "C", "D"])
    agency_rules: Dict[str, List[str]] = field(default_factory=lambda: {
        "BWDB": ["Zone-specific BWDB rates apply"],
        "PWD": ["Zone-specific PWD rates apply"],
        "LGED": ["Zone-specific LGED rates apply"],
    })
    cross_agency_rules: List[str] = field(default_factory=lambda: [
        "Cross-zone work rates apply multiplier",
        "Multi-zone projects require special approval",
    ])


@dataclass
class PPRComplianceConfig:
    nppi_items: Dict[str, NPPIItem] = field(default_factory=lambda: {
        "1.01": NPPIItem("1.01", "Earthworks/Excavation", 1.0, "Rate reduction by 15%", "Site inspection certificate"),
        "1.02": NPPIItem("1.02", "Concrete Works", 1.0, "Rate reduction by 20%", "Mix design approval + lab test report"),
        "2.01": NPPIItem("2.01", "Earthmoving Equipment", 1.0, "No rate application allowed", "Equipment registration + operator certification"),
    })
    slt: SLTRequirements = field(default_factory=SLTRequirements)
    code_patterns: CodePatterns = field(default_factory=CodePatterns)
    billing: BillingCompliance = field(default_factory=BillingCompliance)
    zones: ZoneCompliance = field(default_factory=ZoneCompliance)
    agency_rates: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "BWDB": {"40-200-00": 1500.0, "16-200-00": 1200.0},
        "PWD": {"26.50": 1800.0, "12.1.1.1": 2200.0},
        "LGED": {"4.09": 1600.0, "3.11": 1400.0},
    })
    regional_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "A": 1.0, "B": 0.95, "C": 0.9, "D": 0.85,
    })

    def get_compliance_checks(self, category: str) -> List[str]:
        mapping = {
            "A": ["1.01", "1.02", "1.03", "2.01", "2.02"],
            "B": ["4.01", "4.02", "4.03", "4.04", "4.05"],
            "C": ["6.01", "6.02", "6.03", "6.04"],
            "D": ["7.01", "7.02", "7.03", "7.04"],
        }
        return mapping.get(category.upper(), [])

    def detect_agency(self, code: str) -> Optional[str]:
        if self.code_patterns.bwdb.match(code):
            return "BWDB"
        if self.code_patterns.pwd.match(code):
            return "PWD"
        if self.code_patterns.lged.match(code):
            return "LGED"
        return None

    def validate_rate(self, agency: str, code: str, zone: str) -> Optional[float]:
        rates = self.agency_rates.get(agency.upper(), {})
        base_rate = rates.get(code)
        if base_rate is None:
            return None
        multiplier = self.regional_multipliers.get(zone.upper(), 1.0)
        return base_rate * multiplier


ppr_config = PPRComplianceConfig()
