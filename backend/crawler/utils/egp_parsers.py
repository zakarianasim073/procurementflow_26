from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlencode

from ..framework.logger import get_logger

log = get_logger("crawler.egp_parsers")

BASE_URL = "https://www.eprocure.gov.bd"

# Full parameter set required by TenderDetailsServlet
FULL_TENDER_PARAMS: dict[str, str] = {
    "departmentId": "", "office": "", "procNature": "",
    "procType": "", "procMethod": "0", "tenderId": "0",
    "refNo": "", "pubDtFrm": "", "pubDtTo": "",
    "closeDtFrm": "", "closeDtTo": "", "cpvCategory": "",
    "isFrame": "0", "h": "t",
}

AJAX_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 ProcureFlow National Intelligence Crawler",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_URL,
}


@dataclass
class AgencyInfo:
    code: str = ""
    name: str = ""
    ministry: str = ""


_registry: List[Dict[str, str]] = []
_registry_loaded = False


def _load_registry():
    global _registry, _registry_loaded
    if _registry_loaded:
        return
    for candidate in [
        Path(__file__).resolve().parents[1] / "config" / "agency_registry.json",
        Path(__file__).resolve().parents[2] / "config" / "agency_registry.json",
        Path(__file__).resolve().parents[3] / "crawler" / "config" / "agency_registry.json",
    ]:
        if candidate.exists():
            _registry = json.loads(candidate.read_text(encoding="utf-8"))
            break
    if not _registry:
        log.warning("agency_registry.json not found")
    _registry_loaded = True


def resolve_agency(text: str) -> AgencyInfo:
    if not text:
        return AgencyInfo()
    _load_registry()
    text_upper = text.upper()
    best: Tuple[int, str, str, str] = (0, "", "", "")
    for entry in _registry:
        m = re.search(entry["pattern"], text_upper)
        if m:
            length = len(m.group(0))
            if length > best[0]:
                best = (length, entry["code"], entry["name"], entry["ministry"])
    if best[0]:
        return AgencyInfo(code=best[1], name=best[2], ministry=best[3])
    return AgencyInfo()


def clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def html_rows(html: str) -> List[str]:
    return re.findall(r"<tr[^>]*>.*?</tr>", html or "", flags=re.I | re.S)


def html_cells(row_html: str) -> List[str]:
    return [clean_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.I | re.S)]


def html_links(row_html: str) -> List[str]:
    return [
        urljoin(BASE_URL, unescape(link))
        for link in re.findall(r"""href\s*=\s*["']([^"']+)["']""", row_html, flags=re.I)
    ]


def numeric_id(*values: Any) -> str:
    for value in values:
        m = re.search(r"(?<!\d)(\d{5,12})(?!\d)", str(value or ""))
        if m:
            return m.group(1)
    return ""


def extract_package(*values: Any) -> str:
    for value in values:
        m = re.search(r"(?:Package\s*(?:No|Number|#)?\s*[:\-.]?\s*|Pkg[:\-.]?\s*)?([A-Z0-9]+[-/][A-Z0-9]+(?:[-/][A-Z0-9]+)*)", str(value or ""), re.I)
        if m:
            return m.group(1)
    return ""


def parse_amount(value: Any) -> float:
    if not value:
        return 0.0
    v = str(value).strip()
    v = re.sub(r"[^\d.,]", "", v)
    v = v.replace(",", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def extract_pe_from_cells(cells: List[str]) -> Tuple[str, str, str]:
    if len(cells) < 5:
        return "", "", ""
    pe_text = cells[3].strip() if len(cells) > 3 else ""
    parts = [p.strip() for p in pe_text.split(",")]
    pe_office = parts[-1] if parts else ""
    location = parts[-1] if parts else ""
    agency = resolve_agency(pe_text)
    return pe_office, location, agency.code


def fetch_tender_pages(
    view_type: str = "Live",
    max_pages: int = 1,
    page_size: int = 50,
    timeout: float = 70.0,
) -> List[Dict[str, Any]]:
    """Fetch tender listings via TenderDetailsServlet using httpx.

    Requires ALL parameters + AJAX headers. Returns parsed records.
    """
    import httpx
    all_records: List[Dict[str, Any]] = []
    params = dict(FULL_TENDER_PARAMS)
    params.update({"funName": "AllTenders", "viewType": view_type})

    with httpx.Client(verify=True, follow_redirects=True, timeout=timeout) as client:
        client.headers.update(AJAX_HEADERS)
        client.get(BASE_URL, timeout=timeout)

        for page in range(1, max_pages + 1):
            params["pageNo"] = str(page)
            params["size"] = str(page_size)
            try:
                html = client.post(f"{BASE_URL}/TenderDetailsServlet", data=params, timeout=timeout)
                if len(html.content) < 100:
                    break
                records = parse_tender_rows_detailed(html.text, view_type)
                if not records:
                    break
                all_records.extend(records)
                if len(records) < page_size:
                    break
            except Exception:
                break

    return all_records


async def fetch_tender_pages_async(
    session,
    view_type: str = "Live",
    max_pages: int = 1,
    page_size: int = 50,
    timeout: float = 70.0,
    start_page: int = 1,
    checkpoint_callback=None,
) -> List[Dict[str, Any]]:
    """Async version of fetch_tender_pages with checkpoint support.

    Args:
        session: httpx.AsyncClient or SessionManager with get_client()
        view_type: Live/Archive/AllTenders/Cancel
        max_pages: maximum pages to fetch
        page_size: records per page
        timeout: request timeout
        start_page: page to start from (for resume)
        checkpoint_callback: async fn(current_page, total_records_so_far) called after each page

    Returns list of parsed tender records.
    """
    import httpx
    all_records: List[Dict[str, Any]] = []
    params: dict = dict(FULL_TENDER_PARAMS)
    params.update({"funName": "AllTenders", "viewType": view_type})

    client = session.get_client() if hasattr(session, 'get_client') else session

    client.headers.update(AJAX_HEADERS)
    try:
        await client.get(BASE_URL, timeout=timeout)
    except Exception:
        pass

    for page in range(start_page, max_pages + 1):
        params["pageNo"] = str(page)
        params["size"] = str(page_size)
        try:
            resp = await client.post(
                f"{BASE_URL}/TenderDetailsServlet",
                data=params, timeout=timeout,
            )
            if len(resp.content) < 100:
                break
            records = parse_tender_rows_detailed(resp.text, view_type)
            if not records:
                break
            all_records.extend(records)
            if checkpoint_callback:
                await checkpoint_callback(page, len(all_records))
            if len(records) < page_size:
                break
        except Exception as e:
            log.warning("fetch_page_failed", page=page, view=view_type, error=str(e))
            break

    return all_records


def parse_tender_rows_detailed(html: str, view_type: str = "") -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for row in html_rows(html):
        cells = html_cells(row)
        if len(cells) < 5:
            continue
        joined = " | ".join(cells)
        tender_id = numeric_id(joined)
        if not tender_id:
            continue

        pe_office, location, agency_code = extract_pe_from_cells(cells)
        package_no = extract_package(joined)
        title = cells[2] if len(cells) > 2 else joined
        nature_and_title = cells[2] if len(cells) > 2 else ""
        nature_parts = nature_and_title.split(",", 1)
        procurement_nature = nature_parts[0].strip() if nature_parts else ""

        type_method = cells[4] if len(cells) > 4 else ""
        type_parts = type_method.split(",", 1)
        procurement_type = type_parts[0].strip() if type_parts else ""
        procurement_method = type_parts[1].strip() if len(type_parts) > 1 else ""

        dates_str = cells[5].strip() if len(cells) > 5 else ""
        date_match = re.findall(r"\d{1,2}[-/][A-Za-z]{3,9}[-/]\d{2,4}\s*\d{2}:\d{2}", dates_str)
        publish_date = date_match[0] if date_match else ""
        closing_date = date_match[1] if len(date_match) > 1 else ""

        records.append({
            "source": "egp_tender_details",
            "view_type": view_type,
            "tender_id": tender_id,
            "package_no": package_no,
            "title": title[:1000],
            "procurement_nature": procurement_nature,
            "procurement_type": procurement_type,
            "procurement_method": procurement_method,
            "publish_date": publish_date,
            "closing_date": closing_date,
            "procuring_entity": pe_office,
            "pe_office": pe_office,
            "location": location,
            "district": location.split(",")[0].strip() if "," in location else location,
            "agency_code": agency_code,
        })
    return records


def _parse_pe_chain(pe_text: str) -> Dict[str, str]:
    text = clean_text(pe_text)
    parts = [p.strip() for p in text.split(",")]
    result: Dict[str, str] = {"pe_chain": text}
    if parts:
        result["ministry"] = parts[0]
    if len(parts) > 1:
        result["division"] = parts[1]
    if len(parts) > 2:
        result["organization"] = parts[2]
    if parts:
        result["pe_office"] = parts[-1]
    agency = resolve_agency(text)
    result["agency_code"] = agency.code
    result["agency_name"] = agency.name
    return result


def parse_award_rows_detailed(html: str, keyword: str = "", noa_page: int = 0) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for row in html_rows(html):
        cells = html_cells(row)
        if len(cells) < 8:
            continue
        if cells and not re.search(r"\d", cells[0]):
            continue
        joined = " | ".join(cells)
        tender_id = numeric_id(joined)
        if keyword.isdigit() and tender_id and tender_id != keyword:
            continue
        links = html_links(row)
        detail_links = [link for link in links if "Award" in link or "ViewTender" in link or "ViewAwardedContracts" in link]

        procuring_entity = cells[1] if len(cells) > 1 else ""
        pe_office = cells[3] if len(cells) > 3 else ""
        location_raw = cells[4] if len(cells) > 4 else ""
        title_raw = cells[2] if len(cells) > 2 else joined
        agency = resolve_agency(procuring_entity + " " + title_raw + " " + pe_office)
        package_no = extract_package(joined)

        records.append({
            "source": "ECONTRACT",
            "noa_page": noa_page,
            "tender_id": tender_id,
            "package_no": package_no,
            "title": title_raw[:1000],
            "procuring_entity": procuring_entity,
            "procurement_method": "",
            "pe_office": pe_office,
            "location": location_raw,
            "district": location_raw.strip().split(",")[0] if "," in location_raw else location_raw,
            "award_date": cells[5] if len(cells) > 5 else "",
            "winner": cells[6] if len(cells) > 6 else "",
            "amount_bdt": parse_amount(cells[7] if len(cells) > 7 else ""),
            "detail_url": detail_links[0] if detail_links else "",
            "agency_code": agency.code,
            "agency_name": agency.name,
            "ministry": agency.ministry,
        })
    return records


# ── Award (NOA) httpx-based crawl — mirrors fetch_tender_pages_async ──────────
NOA_PARAMS: dict = {"funName": "NOA", "keyword": ""}


async def fetch_award_pages_async(
    session,
    max_pages: int = 1,
    page_size: int = 50,
    timeout: float = 70.0,
    start_page: int = 1,
    keyword: str = "",
    checkpoint_callback=None,
) -> List[Dict[str, Any]]:
    """Fetch NOA/award listings via SearchNoaServlet using httpx (no Playwright)."""
    import httpx
    all_records: List[Dict[str, Any]] = []
    params: dict = dict(NOA_PARAMS)
    params["keyword"] = keyword
    client = session.get_client() if hasattr(session, "get_client") else session
    client.headers.update(AJAX_HEADERS)
    try:
        await client.get(BASE_URL, timeout=timeout)
    except Exception:
        pass

    for page in range(start_page, max_pages + 1):
        params["pageNo"] = str(page)
        params["size"] = str(page_size)
        try:
            resp = await client.post(
                f"{BASE_URL}/SearchNoaServlet", data=params, timeout=timeout
            )
            if len(resp.content) < 100:
                break
            records = parse_award_rows_detailed(resp.text)
            if not records:
                break
            all_records.extend(records)
            if checkpoint_callback:
                await checkpoint_callback(page, len(all_records))
            if len(records) < page_size:
                break
        except Exception as e:
            log.warning("fetch_award_page_failed", page=page, error=str(e))
            break
    return all_records


def parse_award_detail_html(html: str) -> Dict[str, Any]:
    """Extract award key/value fields from a ViewAwardedContracts.jsp HTML page."""
    text = re.sub(r"<[^>]+>", "\n", html)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    kv: Dict[str, str] = {}
    pat = re.compile(r"^(.+?)\s*:\s*(.*)$")
    i = 0
    while i < len(lines):
        m = pat.match(lines[i])
        if m:
            label, value = m.group(1).strip(), m.group(2).strip()
            if not value and i + 1 < len(lines) and not pat.match(lines[i + 1]):
                value = lines[i + 1].strip()
                i += 1
            kv[label] = value
        i += 1

    def g(*labels: str, default: str = "") -> str:
        for lab in labels:
            for k in kv:
                if k.lower().startswith(lab.lower()):
                    return kv[k]
        return default

    return {
        "reference_no": g("Invitation/Proposal Reference No"),
        "ministry": g("Ministry/Division"),
        "pe_name": g("Procuring Entity Name"),
        "award_for": g("Contract Award for"),
        "procurement_method": g("Procurement Method"),
        "package_no": g("Package No"),
        "contract_value_bdt": g("Contract Value"),
        "economic_operator_name": g("Name of the Economic Operator"),
        "economic_operator_id": g("Tenderer ID of the Economic Operator"),
        "contract_signing_date": g("Date of Contract Signing"),
    }

