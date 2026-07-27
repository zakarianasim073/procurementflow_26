"""W-009 — L6 AgentResult envelope + evidence persistence (Constitution §14).

Every intelligence output ships as: value + confidence + evidence + knowledge_refs
+ rule/model version. Evidence is persisted to P03 via the EPDP client BEFORE the
decision surfaces (core/03 L5). Single home — agents import, never re-implement.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIDENCE_LEVELS = ("LOW", "MEDIUM", "HIGH")

ENVELOPE_KEYS = ("value", "confidence", "evidence", "knowledge_refs", "rule_version")


def build_envelope(
    value: Any,
    confidence: str,
    evidence: List[str],
    rule_version: str,
    knowledge_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Construct the frozen L6 envelope. Raises on malformed inputs — an
    invalid envelope must fail loudly, never surface silently."""
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(f"confidence must be one of {CONFIDENCE_LEVELS}, got {confidence!r}")
    if not rule_version:
        raise ValueError("rule_version is mandatory (L6)")
    return {
        "value": value,
        "confidence": confidence,
        "evidence": list(evidence),
        "knowledge_refs": list(knowledge_refs or []),
        "rule_version": rule_version,
    }


def is_enveloped(output: Dict[str, Any]) -> bool:
    """Test hook: does an agent output carry a complete envelope?"""
    env = output.get("envelope")
    return isinstance(env, dict) and all(k in env for k in ENVELOPE_KEYS) and bool(env["rule_version"])


async def persist_evidence(
    context: Dict[str, Any],
    *,
    claim: str,
    source_reference: str,
    excerpt: Optional[str] = None,
    confidence: float = 1.0,
    clause_number: Optional[str] = None,
    workspace_id: Optional[str] = None,
    decision_ref: Optional[str] = None,
) -> Optional[str]:
    """Persist one evidence item to P03 via the EPDP client found in context.

    The client is injected as context["evidence_client"] (an EPDPClient). When
    absent (offline runs, unit tests without wiring) persistence is skipped and
    logged — surfacing still requires the envelope itself.
    Returns the stored evidence id (X-005: agents put it in knowledge_refs so
    every recommendation points at persisted evidence), or None when unwired.
    """
    client = context.get("evidence_client")
    if client is None:
        logger.debug("evidence_client not wired; skipping remote persistence for: %s", claim[:80])
        return None

    from app.clients.epdp.models import EvidencePayload

    payload = EvidencePayload(
        claim=claim[:1000],
        source_type="agent_finding",
        source_reference=source_reference[:255],
        excerpt=(excerpt or "")[:2000] or None,
        confidence=confidence,
        clause_number=(clause_number or "")[:64] or None,
        workspace_id=workspace_id,
        decision_ref=decision_ref,
    )
    response = await client.post_evidence(payload)
    if not response.stored:
        return None
    evidence_id = response.evidence.get("id")
    return f"evidence:{evidence_id}" if evidence_id else None
