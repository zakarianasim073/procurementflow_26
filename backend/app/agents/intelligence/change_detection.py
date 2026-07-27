"""
Agent 47 - Change Detection Agent
Monitors APP budgets, tender specifications, and corrigenda for mid-tender changes.
Re-triggers analysis when significant changes are detected.
"""

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ChangeDetectionAgent(BaseAgent):
    agent_id = "agent-047-change-detection"
    agent_name = "Change Detection"
    description = "Monitors APP budgets, tender specs, and corrigenda for mid-tender changes"
    dependencies = ["agent-003-corrigendum-watchdog"]
    version = "1.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_id = context.get("tender_id", "")
        if not tender_id:
            return AgentResult(
                status=AgentStatus.SKIPPED,
                output={"message": "No tender_id provided for change detection"}
            )
        
        changes_detected = []
        
        # ── 1. Check for corrigenda / addenda ──────────────────────────────
        corrigenda = context.get("corrigenda", [])
        for corr in corrigenda:
            if corr.get("is_new", False):
                changes_detected.append({
                    "type": "corrigendum",
                    "severity": "high",
                    "description": f"New corrigendum published: {corr.get('subject', '')}",
                    "published_date": corr.get("date", ""),
                })
        
        # ── 2. Check APP budget changes ────────────────────────────────────
        current_budget = context.get("current_budget", 0)
        previous_budget = context.get("previous_budget", 0)
        if current_budget and previous_budget and current_budget != previous_budget:
            variance = abs(current_budget - previous_budget) / previous_budget if previous_budget else 0
            severity = "high" if variance > 0.20 else "medium" if variance > 0.10 else "low"
            changes_detected.append({
                "type": "app_budget_change",
                "severity": severity,
                "description": f"APP budget changed from {previous_budget:,.2f} to {current_budget:,.2f} ({variance:.1%})",
                "variance_pct": round(variance * 100, 2),
            })
        
        # ── 3. Check specification changes ─────────────────────────────────
        current_spec_hash = context.get("spec_hash", "")
        previous_spec_hash = context.get("previous_spec_hash", "")
        if current_spec_hash and previous_spec_hash and current_spec_hash != previous_spec_hash:
            changes_detected.append({
                "type": "specification_change",
                "severity": "high",
                "description": "Technical specifications have been modified",
            })
        
        # ── 4. Check deadline extension ────────────────────────────────────
        current_deadline = context.get("deadline", "")
        previous_deadline = context.get("previous_deadline", "")
        if current_deadline and previous_deadline and current_deadline != previous_deadline:
            changes_detected.append({
                "type": "deadline_extension",
                "severity": "medium",
                "description": f"Deadline changed from {previous_deadline} to {current_deadline}",
            })
        
        # ── 5. Determine re-analysis triggers ──────────────────────────────
        triggers = []
        high_changes = [c for c in changes_detected if c["severity"] == "high"]
        medium_changes = [c for c in changes_detected if c["severity"] == "medium"]
        
        if high_changes:
            triggers.append({
                "action": "re_run_full_pipeline",
                "reason": f"{len(high_changes)} high-severity changes detected",
                "priority": "urgent",
            })
        elif medium_changes:
            triggers.append({
                "action": "re_run_evaluation_phase",
                "reason": f"{len(medium_changes)} medium-severity changes detected",
                "priority": "normal",
            })
        
        result = {
            "tender_id": tender_id,
            "changes_detected": changes_detected,
            "change_count": len(changes_detected),
            "high_severity_count": len(high_changes),
            "medium_severity_count": len(medium_changes),
            "low_severity_count": len([c for c in changes_detected if c["severity"] == "low"]),
            "re_analysis_triggers": triggers,
            "needs_re_analysis": len(triggers) > 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if self.brain:
            try:
                await self.share_knowledge(
                    entry_type="change_detection",
                    tender_id=tender_id,
                    data=result,
                    summary=f"Change detection: {len(changes_detected)} changes ({len(high_changes)} high severity)",
                    tags=["change_detection", "monitoring"],
                )
            except Exception as exc:
                logger.warning("Change detection knowledge share failed: %s", exc)
        
        return AgentResult(status=AgentStatus.SUCCESS, output=result)
