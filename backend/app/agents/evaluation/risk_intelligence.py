"""
Agent 8 — Risk Intelligence Agent
Identifies contractual risks: LD analysis, guarantee analysis, retention, insurance.
Uses LLM or document parsing for actual values instead of hardcoded constants.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agent_schemas import RiskProfile

logger = logging.getLogger(__name__)


class RiskIntelligenceAgent(BaseAgent):
    agent_id = "agent-008-risk-intelligence"
    agent_name = "Risk Intelligence Agent"
    description = "Analyzes contractual risks including liquidated damages, guarantees, retentions, and insurance requirements from tender documents."
    dependencies: List[str] = ["agent-004-document-ai"]
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_profile = context.get("upstream", {}).get("agent-004-document-ai", {})
        tender_info = context.get("tender_info", {})

        risk = await self._analyze_risks(tender_profile, tender_info)

        output = {
            "risk_level": risk.risk_level,
            "ld_analysis": {
                "rate": risk.ld_rate,
                "assessment": risk.ld_risk,
            },
            "guarantee_analysis": {
                "required": risk.guarantee_required,
                "assessment": risk.guarantee_risk,
            },
            "retention_analysis": {
                "percent": risk.retention_percent,
                "assessment": risk.retention_risk,
            },
            "insurance_requirements": risk.insurance_requirements,
            "risk_factors": risk.risk_factors,
        }

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=output,
        )

    async def _analyze_risks(self, profile: Dict, tender_info: Dict) -> RiskProfile:
        risk = RiskProfile()
        emd = profile.get("emd_amount", 0)
        est_value = tender_info.get("estimated_value", 0) or tender_info.get("estimated_amount_bdt", 0)
        
        # Extract LD rate from document if available, otherwise use standard PPR default
        sections = profile.get("sections_extracted", [])
        ld_rate = self._extract_ld_rate(profile)
        
        # LD Analysis
        risk.ld_rate = ld_rate
        if ld_rate > 0.0015:
            risk.ld_risk = f"High LD rate: {ld_rate*100:.2f}% per day"
        elif ld_rate > 0:
            risk.ld_risk = f"Standard LD rate: {ld_rate*100:.2f}% per day"
        else:
            risk.ld_risk = "LD rate not specified in document — using PPR default 0.1% per day"
            risk.ld_rate = 0.001

        # Guarantee — use extracted EMD if available
        if emd > 0:
            risk.guarantee_required = emd
            risk.guarantee_risk = f"Performance Guarantee based on EMD of ৳{emd:,.0f}"
        else:
            risk.guarantee_required = 0
            risk.guarantee_risk = "EMD amount not extracted — check tender document"

        # Retention — standard 5% per PPR, but check if document specifies different
        retention = self._extract_retention(profile)
        risk.retention_percent = retention
        risk.retention_risk = f"{retention}% retention on interim payments"

        # Insurance — extract from document or use standard
        insurance = self._extract_insurance(profile)
        risk.insurance_requirements = insurance

        # Overall risk assessment
        risk.risk_factors = []
        if emd > 0:
            risk.risk_factors.append(f"EMD of ৳{emd:,.0f}")
        risk.risk_factors.append(f"LD rate: {risk.ld_rate*100}%/day")
        risk.risk_factors.append(f"Retention: {risk.retention_percent}%")

        # Determine risk level based on actual values
        risk.risk_level = "Low"
        if est_value > 100_000_000 or emd > 1_000_000:
            risk.risk_level = "High"
        elif est_value > 50_000_000 or emd > 500_000:
            risk.risk_level = "Medium"

        return risk

    def _extract_ld_rate(self, profile: Dict) -> float:
        """Try to extract LD rate from document text."""
        import re
        sections = profile.get("sections", {})
        for section_text in sections.values():
            if isinstance(section_text, str):
                # Look for patterns like "0.1% per day", "0.05% per week", etc.
                m = re.search(r'(\d+\.?\d*)\s*%\s*(?:per|/)\s*(?:day|week|month)', section_text, re.IGNORECASE)
                if m:
                    rate = float(m.group(1)) / 100
                    return rate
        return 0.0

    def _extract_retention(self, profile: Dict) -> float:
        """Try to extract retention percentage from document text."""
        import re
        sections = profile.get("sections", {})
        for section_text in sections.values():
            if isinstance(section_text, str):
                m = re.search(r'(\d+\.?\d*)\s*%\s*retention', section_text, re.IGNORECASE)
                if m:
                    return float(m.group(1))
        return 5.0  # Standard PPR default

    def _extract_insurance(self, profile: Dict) -> List[str]:
        """Extract insurance requirements from document text."""
        import re
        sections = profile.get("sections", {})
        insurance_types = []
        for section_text in sections.values():
            if isinstance(section_text, str):
                text_lower = section_text.lower()
                if "contractor's all risk" in text_lower or "car insurance" in text_lower:
                    insurance_types.append("CAR Insurance (Contractor's All Risk)")
                if "third party liability" in text_lower:
                    insurance_types.append("Third Party Liability Insurance")
                if "workmen's compensation" in text_lower or "workmen compensation" in text_lower:
                    insurance_types.append("Workmen's Compensation Insurance")
        if not insurance_types:
            insurance_types = ["Check tender document for insurance requirements"]
        return insurance_types
