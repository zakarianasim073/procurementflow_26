"""Deterministic procuring-entity to agency normalization."""

from __future__ import annotations

from typing import Optional, Tuple


_AGENCY_MARKERS: tuple[tuple[str, str, float], ...] = (
    ("bangladesh water development board", "BWDB", 0.98),
    ("bangladesh water development", "BWDB", 0.95),
    ("water development board", "BWDB", 0.94),
    ("bwdb", "BWDB", 0.99),
    ("public works department", "PWD", 0.98),
    ("public works", "PWD", 0.94),
    ("pwd", "PWD", 0.99),
    ("local government engineering department", "LGED", 0.98),
    ("local government engineering", "LGED", 0.95),
    ("lged", "LGED", 0.99),
    ("roads and highways department", "RHD", 0.98),
    ("roads and highways", "RHD", 0.95),
    ("road transport and highways", "RHD", 0.90),
    ("rhd", "RHD", 0.99),
    ("department of public health engineering", "DPHE", 0.98),
    ("public health engineering", "DPHE", 0.94),
    ("dphe", "DPHE", 0.99),
    ("bangladesh agricultural development corporation", "BADC", 0.98),
    ("agricultural development corporation", "BADC", 0.94),
    ("badc", "BADC", 0.99),
    ("rural electrification board", "BREB", 0.96),
    ("rural electrification", "BREB", 0.92),
    ("breb", "BREB", 0.99),
)

_FALLBACK_MARKERS: tuple[tuple[tuple[str, ...], str, float], ...] = (
    (("water", "irrigation"), "BWDB", 0.62),
    (("embankment", "flood", "drainage"), "BWDB", 0.58),
    (("road", "highway", "bridge", "culvert"), "RHD", 0.56),
    (("upazila", "union parishad", "local gov"), "LGED", 0.58),
    (("building", "civil surgeon", "public works"), "PWD", 0.55),
)


def extract_agency_with_confidence(
    procuring_entity: Optional[str] = "",
    office: Optional[str] = "",
    title: Optional[str] = "",
    agency_code: Optional[str] = "",
) -> Tuple[str, float]:
    """Return normalized agency id and confidence for award/tender records."""
    explicit = (agency_code or "").strip().upper()
    if explicit and explicit not in {"UNKNOWN", "OTHER", "N/A", "NA", "NULL"}:
        return explicit[:20], 1.0

    text = " ".join(str(v or "") for v in (procuring_entity, office, title)).lower()
    if not text.strip():
        return "UNKNOWN", 0.0

    for marker, agency, confidence in _AGENCY_MARKERS:
        if marker in text:
            return agency, confidence

    for markers, agency, confidence in _FALLBACK_MARKERS:
        if any(marker in text for marker in markers):
            return agency, confidence

    return "UNKNOWN", 0.0


def extract_agency_id(procuring_entity: Optional[str] = "", office: Optional[str] = "") -> str:
    return extract_agency_with_confidence(procuring_entity=procuring_entity, office=office)[0]
