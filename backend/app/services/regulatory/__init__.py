"""Regulatory Compliance Engine — versioned Rule Registry + single Rule Engine.

No application code should contain procurement formulas directly; everything
routes through `rule_engine` (see rule_engine.py), which resolves the
applicable RuleVersion for a given date and dispatches to formulas.py.
"""
from .rule_engine import rule_engine, RuleEngine, RuleExecutionResult  # noqa: F401
