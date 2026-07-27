from __future__ import annotations

import re
from typing import Any, Dict, Optional

_KNOWN_LABELS = (
    "Work Experience Certificate No",
    "Ministry/Division",
    "PE Office Name",
    "Organization Name",
    "PE Name",
    "Tender ID",
    "Tender Ref No",
    "Package Name",
    "Package No",
    "Procurement Nature",
    "Procurement Method",
    "Work Category",
    "Name of Work",
    "Work Completion Status",
    "Tender Publication Date",
    "Tender Type",
    "Work Status",
    "Contract Start Date",
    "Contract End Date",
    "Contract No.",
    "Contract Value (Equivalent in BDT)",
    "Physical Progress (%)",
    "Financial Progress (%)",
    "Date of Physical Progress",
    "Date of Financial Progress",
    "Company Name",
    "Is JVCA",
    "Remarks",
    "Comments By PE",
)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().strip(":").strip()


def _field(text: str, label: str, next_labels: tuple[str, ...] = ()) -> str:
    boundary_labels = tuple(dict.fromkeys((
        *next_labels,
        *(v for v in _KNOWN_LABELS if v.lower() != label.lower()),
    )))
    labels = "|".join(re.escape(v) for v in boundary_labels)
    boundary = rf"(?=\s*(?:{labels})\s*:|\s*(?:{labels})\b|$)" if labels else r"(?=$)"
    pattern = rf"{re.escape(label)}\s*:?\s*(.*?){boundary}"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return _clean(match.group(1)) if match else ""


def _numeric_tender_id(value: Any) -> Optional[str]:
    match = re.search(r"(?<!\d)(\d{5,12})(?!\d)", str(value or ""))
    return match.group(1) if match else None


def parse_eexperience_detail(text: str, source_url: str = "") -> Dict[str, Any]:
    """Parse e-GP VieweCmsDetails text into the canonical eExperience schema."""
    raw_text = str(text or "")
    try:
        from bs4 import BeautifulSoup

        raw_text = BeautifulSoup(raw_text, "html.parser").get_text("\n")
    except Exception:
        raw_text = re.sub(r"<[^>]+>", "\n", raw_text)

    normalized = re.sub(r"[ \t]+", " ", raw_text)
    normalized = re.sub(r"\s*:\s*", ": ", normalized)
    normalized = re.sub(r"\n+", "\n", normalized)
    normalized = re.sub(
        r"\b(Work Experience Certificate No|Ministry/Division|PE Office Name|Organization Name|PE Name|"
        r"Tender ID|Tender Ref No|Package Name|Package No|Procurement Nature|Procurement Method|"
        r"Work Category|Name of Work|Work Completion Status|Tender Publication Date|Tender Type|Work Status|"
        r"Contract Start Date|Contract End Date|Contract No\.|Contract Value \(Equivalent in BDT\)|"
        r"Physical Progress \(%\)|Financial Progress \(%\)|Date of Physical Progress|"
        r"Date of Financial Progress|Company Name|Is JVCA|Remarks|Comments By PE)\b\s*:?\s*",
        lambda m: f"\n{m.group(1)}: ",
        normalized,
        flags=re.IGNORECASE,
    )
    tender_id = _numeric_tender_id(_field(normalized, "Tender ID", ("Tender Ref No",)))
    package_no = _field(normalized, "Package No", ("Procurement Nature",))
    package_name = _field(normalized, "Package Name", ("Package No",))
    return {
        "tender_id": tender_id,
        "tender_ref_no": _field(normalized, "Tender Ref No", ("Package Name",)),
        "package_name": package_name,
        "package_no": package_no,
        "procurement_nature": _field(normalized, "Procurement Nature", ("Procurement Method",)),
        "procurement_method": _field(normalized, "Procurement Method", ("Work Category",)),
        "work_category": _field(normalized, "Work Category", ("Name of Work",)),
        "name_of_work": _field(normalized, "Name of Work", ("Work Completion Status",)),
        "title": package_name or _field(normalized, "Name of Work", ("Work Completion Status",)),
        "completion_status": _field(normalized, "Work Completion Status", ("Tender Publication Date",)),
        "published_date": _field(normalized, "Tender Publication Date", ("Tender Type",)),
        "tender_type": _field(normalized, "Tender Type", ("Work Status",)),
        "contract_start_date": _field(normalized, "Contract Start Date", ("Contract End Date",)),
        "contract_end_date": _field(normalized, "Contract End Date", ("Contract No.",)),
        "contract_no": _field(normalized, "Contract No.", ("Contract Value (Equivalent in BDT)",)),
        "contract_value_bdt": _field(normalized, "Contract Value (Equivalent in BDT)", ("Physical Progress",)),
        "physical_progress_pct": _field(normalized, "Physical Progress (%)", ("Financial Progress",)),
        "financial_progress_pct": _field(normalized, "Financial Progress (%)", ("Date of Physical Progress",)),
        "physical_progress_date": _field(normalized, "Date of Physical Progress", ("Date of Financial Progress",)),
        "financial_progress_date": _field(normalized, "Date of Financial Progress", ("Company Name",)),
        "contractor_name": _field(normalized, "Company Name", ("Is JVCA",)),
        "is_jvca": _field(normalized, "Is JVCA", ("Remarks",)).upper() in {"YES", "Y", "TRUE", "1"},
        "remarks": _field(normalized, "Remarks", ("Comments By PE",)),
        "comments_by_pe": _field(normalized, "Comments By PE"),
        "experience_certificate_no": _field(normalized, "Work Experience Certificate No", ("PROCURING ENTITY",)),
        "ministry_division": _field(normalized, "Ministry/Division", ("PE Office Name",)),
        "pe_office": _field(normalized, "PE Office Name", ("Organization Name",)),
        "organization_name": _field(normalized, "Organization Name", ("PE Name",)),
        "pe_name": _field(normalized, "PE Name", ("TENDER INFORMATION",)),
        "source_url": source_url,
    }
