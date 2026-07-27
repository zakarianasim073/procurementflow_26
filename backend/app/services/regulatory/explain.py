"""Explanation Engine — renders a RuleExecutionResult into human-readable text.

Templates are plain str.format() strings stored on RuleVersion.explanation_template
(not Jinja2 — matches codebase convention, and there's no injection risk since
only trusted DB-stored templates are ever formatted, never user input).
"""
from __future__ import annotations

from typing import Any, Dict, List


DEFAULT_TEMPLATE = "{decision} — {citation}"


def render_explanation(
    explanation_template: str | None,
    *,
    decision: str,
    outputs: Dict[str, Any],
    intermediate_values: Dict[str, Any],
    citations: List[str],
) -> str:
    """Render a rule's stored template against its execution outputs.

    Falls back to a terse default if the template is missing or references
    a key that isn't present in the outputs (never raises on a formatting
    error — an explanation string must never block returning a decision).
    """
    template = explanation_template or DEFAULT_TEMPLATE
    citation = ", ".join(citations) if citations else "no citation on file"
    context = {**intermediate_values, **outputs, "decision": decision, "citation": citation}
    try:
        return template.format(**context)
    except (KeyError, IndexError, ValueError):
        return f"{decision} — {citation}"
