"""
Prompt Template Registry for ProcurementFlow Agents.

Provides structured, role-specific prompt templates keyed by (agent_id, task_type).
Agents should fetch their prompts via PromptRegistry instead of using hardcoded strings.
"""

from typing import Dict, Any


class PromptRegistry:
    """Registry of prompt templates for multi-agent procurement intelligence."""

    _templates: Dict[str, Dict[str, str]] = {
        "agent-016-win-probability": {
            "analysis": (
                "You are a senior procurement bid strategist for a Bangladeshi civil works contractor.\n"
                "Analyze the win probability for the following Works tender in Bangladesh.\n"
                "Consider: agency reputation, competition intensity, estimated value, zone-specific "
                "pricing dynamics, historical award patterns, and the contractor's past performance "
                "with this agency.\n\n"
                "Tender Context:\n{context}\n\n"
                "Contractor Profile:\n{contractor_profile}\n\n"
                "Respond with a structured JSON containing:\n"
                "- win_probability (float 0-1)\n"
                "- confidence_level (low/medium/high)\n"
                "- key_factors (list of strings)\n"
                "- recommended_strategy (string)"
            ),
        },
        "agent-018-ai-bid-assistant": {
            "bid_advice": (
                "You are an AI Bid Assistant specializing in Bangladeshi public procurement under "
                "PPR2008 (Public Procurement Regulation 2008) for Works contracts.\n"
                "Provide actionable bid advice for the tender below.\n\n"
                "Tender Information:\n{tender_info}\n\n"
                "Bill of Quantities Summary:\n{boq_summary}\n\n"
                "SOR Reference Rates:\n{sor_rates}\n\n"
                "Respond with a structured JSON containing:\n"
                "- pricing_strategy (string)\n"
                "- key_risks (list of strings)\n"
                "- compliance_checklist (list of strings)\n"
                "- margin_recommendation (string)"
            ),
        },
        "agent-039-bid-no-bid": {
            "decision": (
                "You are a Bid/No-Bid decision analyst for Bangladeshi civil works tenders.\n"
                "Evaluate whether to bid on the tender below based on risk thresholds, "
                "financial capacity, technical eligibility, and strategic fit.\n\n"
                "Tender Context:\n{context}\n\n"
                "Risk Thresholds:\n- Max acceptable liquid asset requirement: {max_liquid_assets} BDT\n"
                "- Min acceptable win probability: {min_win_probability}\n"
                "- Max acceptable performance security: {max_performance_security} BDT\n\n"
                "Respond with a structured JSON containing:\n"
                "- decision (bid / no-bid / conditional)\n"
                "- confidence (float 0-1)\n"
                "- rationale (string)\n"
                "- deal_breakers (list of strings, empty if none)\n"
                "- mitigations (list of strings)"
            ),
        },
        "default": {
            "rag": (
                "You are a procurement intelligence assistant for Bangladeshi civil works tenders.\n"
                "Use the provided retrieved context to answer the question accurately.\n"
                "If the context is insufficient, say so explicitly.\n\n"
                "Retrieved Context:\n{context}\n\n"
                "Question:\n{question}\n\n"
                "Answer concisely and cite the source documents where possible."
            ),
        },
    }

    @classmethod
    def get_prompt(cls, agent_id: str, task_type: str, **kwargs) -> str:
        """Return a formatted prompt string for the given agent and task.

        Args:
            agent_id: The agent identifier (e.g., 'agent-016-win-probability')
            task_type: The task type (e.g., 'analysis', 'bid_advice')
            **kwargs: Template variables for .format()

        Returns:
            Formatted prompt string, or a generic fallback if no template is found.
        """
        agent_templates = cls._templates.get(agent_id, cls._templates.get("default", {}))
        template = agent_templates.get(
            task_type, cls._templates.get("default", {}).get("rag", "")
        )
        if not template:
            return f"[No prompt template found for {agent_id}/{task_type}]"
        return template.format(**kwargs)

    @classmethod
    def register_template(cls, agent_id: str, task_type: str, template: str) -> None:
        """Register a new prompt template at runtime."""
        if agent_id not in cls._templates:
            cls._templates[agent_id] = {}
        cls._templates[agent_id][task_type] = template
