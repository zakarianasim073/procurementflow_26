"""
Agent 7 — Eligibility & Compliance Agent
Checks qualification requirements: experience, turnover, similar works, equipment, personnel, licenses.
Reads equipment requirements from tender specs instead of hardcoded set.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.core.envelope import build_envelope, persist_evidence
from app.agent_schemas import EligibilityCriteria
from app.db.database import get_async_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class EligibilityComplianceAgent(BaseAgent):
    agent_id = "agent-007-eligibility-compliance"
    agent_name = "Eligibility & Compliance Agent"
    description = "Checks all qualification criteria including experience, turnover, equipment, personnel, and licenses."
    dependencies: List[str] = ["agent-004-document-ai", "agent-006-spec-intelligence"]
    version = "2.1.0"

    DEFAULT_MIN_ENGINEERS = 5  # PPR works-tender floor when TDS omits personnel counts

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        company_profile = context.get("company_profile", {})
        tender_requirements = context.get("upstream", {}).get("agent-004-document-ai", {})
        specs = context.get("upstream", {}).get("agent-006-spec-intelligence", {})

        criteria = await self._check_eligibility(company_profile, tender_requirements, specs)

        output = {
            "compliant": criteria.compliant,
            "checks": {
                "experience_met": criteria.experience_met,
                "turnover_met": criteria.turnover_met,
                "similar_works_met": criteria.similar_works_met,
                "equipment_met": criteria.equipment_met,
                "personnel_met": criteria.personnel_met,
                "licenses_met": criteria.licenses_met,
            },
            "missing_items": criteria.missing_items,
            "notes": criteria.notes,
        }

        # W-009/X-005: persist evidence FIRST, then the envelope references it —
        # every recommendation points at a stored P03 evidence row.
        evidence_lines = criteria.missing_items or [criteria.notes]
        decision = "qualified" if criteria.compliant else "not_qualified"
        evidence_ref = await persist_evidence(
            context,
            claim=f"Qualification {decision}: {output.get('checks')}",
            source_reference=f"{self.agent_id}@{self.version}",
            excerpt="; ".join(evidence_lines),
            workspace_id=context.get("workspace_id") or context.get("tender_id"),
            decision_ref=f"qualification:{decision}",
        )
        output["envelope"] = build_envelope(
            value={"compliant": criteria.compliant, "checks": output["checks"]},
            confidence="HIGH",
            evidence=evidence_lines,
            rule_version=f"qualification-rules v{self.version}",
            knowledge_refs=[evidence_ref] if evidence_ref else [],
        )

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=output,
        )

    async def _check_eligibility(self, company: Dict, requirements: Dict, specs: Dict) -> EligibilityCriteria:
        criteria = EligibilityCriteria()

        company_name = company.get("company_name", company.get("name", ""))
        company_exp = company.get("years_experience", 0)
        company_turnover = company.get("avg_turnover", 0)
        company_equipment = set(company.get("equipment", []))
        company_engineers = company.get("engineers_count", 0)
        company_licenses = set(company.get("licenses", []))

        # Try to get real contractor data from DB if company not specified
        if not company_name and not company_exp and not company_turnover:
            try:
                async with get_async_session() as session:
                    row = (await session.execute(text("""
                        SELECT contractor_name, total_amount_bdt, total_contracts,
                               first_award_date, last_award_date
                        FROM contractors
                        ORDER BY total_amount_bdt DESC
                        LIMIT 1
                    """))).fetchone()
                    if row:
                        company_name = row[0]
                        company_turnover = float(row[1]) if row[1] else 0
                        company_exp = 5
            except Exception as e:
                logger.warning(f"DB contractor lookup failed: {e}")
                # company_exp / company_turnover remain at defaults (0), which safely evaluates to non-compliant

        req_exp = self._parse_experience(requirements.get("experience_required", "5 years"))
        criteria.experience_met = company_exp >= req_exp if company_exp > 0 else False

        req_turnover = requirements.get("turnover_required", 0) or 0
        criteria.turnover_met = company_turnover >= req_turnover if company_turnover > 0 and req_turnover > 0 else False

        # Read required equipment from tender specs instead of hardcoded set
        required_equipment = self._extract_required_equipment(specs)
        if not required_equipment:
            # Fallback: if no specs provided, note that equipment requirements are unknown
            required_equipment = set()
            criteria.equipment_met = len(company_equipment) > 0 if company_equipment else False
            criteria.notes = "Equipment requirements not specified in tender"
        else:
            missing_eq = required_equipment - company_equipment if company_equipment else required_equipment
            criteria.equipment_met = len(missing_eq) == 0

        criteria.personnel_met = (
            company_engineers >= self.DEFAULT_MIN_ENGINEERS if company_engineers > 0 else False
        )
        criteria.licenses_met = len(company_licenses) >= 1 if company_licenses else False

        # Similar works (TDS): count of completed works meeting the minimum single-work
        # value must reach the required count; absent requirement = criterion waived.
        req_similar_count = int(requirements.get("similar_works_required", 0) or 0)
        min_work_value = float(requirements.get("min_similar_work_value_bdt", 0) or 0)
        works = company.get("similar_works", []) or []
        qualifying_works = [
            w for w in works
            if float((w.get("value_bdt", 0) if isinstance(w, dict) else 0) or 0) >= min_work_value
        ]
        criteria.similar_works_met = (
            len(qualifying_works) >= req_similar_count if req_similar_count > 0 else True
        )

        criteria.compliant = all([
            criteria.experience_met, criteria.turnover_met,
            criteria.similar_works_met,
            criteria.equipment_met, criteria.personnel_met,
            criteria.licenses_met,
        ])

        if required_equipment and not criteria.equipment_met:
            missing_eq = required_equipment - company_equipment if company_equipment else required_equipment
            if missing_eq:
                criteria.missing_items.append(f"Missing equipment: {', '.join(missing_eq)}")
        if not criteria.experience_met:
            criteria.missing_items.append(f"Need {req_exp} years experience, have {company_exp}")
        if not criteria.turnover_met and req_turnover > 0:
            criteria.missing_items.append(f"Need turnover >= {req_turnover:,.0f}, have {company_turnover:,.0f}")
        if not criteria.similar_works_met:
            criteria.missing_items.append(
                f"Need {req_similar_count} similar works"
                + (f" of >= {min_work_value:,.0f} BDT each" if min_work_value else "")
                + f", have {len(qualifying_works)}"
            )
        if not criteria.personnel_met:
            criteria.missing_items.append(
                f"Need >= {self.DEFAULT_MIN_ENGINEERS} engineers, have {company_engineers}"
            )
        if not criteria.licenses_met:
            criteria.missing_items.append("No valid trade license on profile")

        criteria.notes = "All criteria met" if criteria.compliant else "Some criteria not met"
        return criteria

    def _parse_experience(self, exp_str: str) -> int:
        import re
        match = re.search(r'(\d+)', str(exp_str))
        return int(match.group(1)) if match else 5

    def _extract_required_equipment(self, specs: Dict) -> set:
        """Extract required equipment from tender specs."""
        equipment = set()
        if not specs:
            return equipment
        
        # Check for equipment list in specs
        spec_equipment = specs.get("required_equipment", specs.get("equipment", []))
        if isinstance(spec_equipment, list):
            equipment.update(str(e) for e in spec_equipment if e)
        elif isinstance(spec_equipment, str):
            # Try to parse comma-separated list
            equipment.update(e.strip() for e in spec_equipment.split(",") if e.strip())
        
        return equipment
