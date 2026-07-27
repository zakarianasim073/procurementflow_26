"""
Agent 46 - Data Quality Validator
Validates BOQ consistency, missing specs, and contradictory requirements.
Runs as a gate after Document AI and before Evaluation agents.
"""

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataQualityValidatorAgent(BaseAgent):
    agent_id = "agent-046-data-quality-validator"
    agent_name = "Data Quality Validator"
    description = "Validates BOQ consistency, missing specs, and contradictory requirements"
    dependencies = ["agent-004-document-ai"]
    version = "1.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        issues: List[Dict[str, Any]] = []
        warnings: List[str] = []
        
        boq_items = context.get("boq_items", [])
        spec_text = context.get("spec_text", "")
        tds_text = context.get("tds_text", "")
        tender_id = context.get("tender_id", "")
        
        # ── 1. BOQ consistency checks ──────────────────────────────────────
        if boq_items:
            # Check for duplicate item codes
            seen_codes = {}
            for item in boq_items:
                code = item.get("code", "")
                if code:
                    if code in seen_codes:
                        issues.append({
                            "severity": "error",
                            "type": "duplicate_boq_code",
                            "item_code": code,
                            "message": f"Duplicate BOQ item code: {code}",
                        })
                    seen_codes[code] = item
            
            # Check for zero or negative quantities
            for item in boq_items:
                qty = item.get("quantity", 0)
                if qty is not None and qty <= 0:
                    issues.append({
                        "severity": "error",
                        "type": "invalid_quantity",
                        "item_code": item.get("code", ""),
                        "message": f"Item {item.get('code', '')} has invalid quantity: {qty}",
                    })
            
            # Check for missing unit prices
            for item in boq_items:
                if "estimated_rate" not in item and "unit_price" not in item:
                    warnings.append(f"Item {item.get('code', '')} has no estimated rate")
            
            # Check total cost consistency
            total_from_items = sum(
                (item.get("quantity", 0) or 0) * (item.get("estimated_rate", 0) or 0)
                for item in boq_items
            )
            stated_total = context.get("total_estimated_cost", 0)
            if stated_total and total_from_items > 0:
                variance = abs(total_from_items - stated_total) / stated_total
                if variance > 0.05:  # 5% tolerance
                    issues.append({
                        "severity": "warning",
                        "type": "cost_variance",
                        "message": f"BOQ total ({total_from_items:,.2f}) differs from stated total ({stated_total:,.2f}) by {variance:.1%}",
                    })
        else:
            warnings.append("No BOQ items found in context")
        
        # ── 2. Missing specs check ─────────────────────────────────────────
        required_sections = ["scope_of_work", "technical_specifications", "general_conditions"]
        for section in required_sections:
            if section not in context and section not in str(spec_text).lower():
                warnings.append(f"Missing or empty section: {section}")
        
        if not spec_text or len(str(spec_text)) < 100:
            issues.append({
                "severity": "warning",
                "type": "missing_specs",
                "message": "Technical specifications appear incomplete or missing",
            })
        
        # ── 3. Contradictory requirements ──────────────────────────────────
        contradictions = self._detect_contradictions(context)
        issues.extend(contradictions)
        
        # ── 4. Summary ─────────────────────────────────────────────────────
        errors = [i for i in issues if i.get("severity") == "error"]
        quality_score = max(0, 100 - len(errors) * 20 - len(warnings) * 5)
        
        is_valid = len(errors) == 0
        
        result = {
            "valid": is_valid,
            "quality_score": quality_score,
            "errors": errors,
            "warnings": warnings,
            "total_issues": len(issues) + len(warnings),
            "tender_id": tender_id,
        }
        
        if self.brain:
            try:
                await self.share_knowledge(
                    entry_type="data_quality_check",
                    tender_id=tender_id,
                    data=result,
                    summary=f"Data quality: {quality_score}/100 ({len(errors)} errors, {len(warnings)} warnings)",
                    tags=["data_quality", "validation"],
                )
            except Exception as exc:
                logger.warning("Data quality knowledge share failed: %s", exc)
        
        status = AgentStatus.SUCCESS if is_valid else AgentStatus.FAILED
        return AgentResult(status=status, output=result)
    
    def _detect_contradictions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect contradictory requirements in tender documents."""
        issues = []
        
        tds = str(context.get("tds_text", "")).lower()
        spec = str(context.get("spec_text", "")).lower()
        
        # Check for contradictory completion dates
        if "completion within 12 months" in tds and "completion within 6 months" in tds:
            issues.append({
                "severity": "error",
                "type": "contradictory_deadline",
                "message": "TDS contains contradictory completion periods (6 vs 12 months)",
            })
        
        # Check for contradictory payment terms
        if "advance payment" in tds and "no advance payment" in tds:
            issues.append({
                "severity": "error",
                "type": "contradictory_payment",
                "message": "Contradictory advance payment terms detected",
            })
        
        # Check for SOR agency mismatch
        boq_agency = context.get("detected_sor_agency", "")
        tds_agency = context.get("tds_agency", "")
        if boq_agency and tds_agency and boq_agency != tds_agency:
            issues.append({
                "severity": "warning",
                "type": "agency_mismatch",
                "message": f"BOQ agency ({boq_agency}) differs from TDS agency ({tds_agency})",
            })
        
        return issues
