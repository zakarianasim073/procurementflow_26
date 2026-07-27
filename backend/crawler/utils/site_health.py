from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from ..framework.logger import get_logger

log = get_logger("crawler.site_health")

MAINTENANCE_MARKERS = [
    "will remain temporarily unavailable",
    "scheduled maintenance activities of the e-GP System",
    "under maintenance",
]
DEFAULT_TIMEOUT = 20.0


@dataclass
class SiteHealthReport:
    url: str
    http_status_ok: bool = False
    hit_maintenance: bool = False
    content_length: int = 0
    link_texts: List[str] = field(default_factory=list)
    link_hrefs_sample: List[str] = field(default_factory=list)
    budget_type_candidates: List[Dict[str, str]] = field(default_factory=list)
    table_count: int = 0
    table_row_counts: List[int] = field(default_factory=list)
    form_field_names: List[str] = field(default_factory=list)
    selectors_seen: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_healthy(self) -> bool:
        return not self.hit_maintenance and self.http_status_ok and self.table_count > 0


def check_maintenance(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in MAINTENANCE_MARKERS)


def diagnose_page(url: str, save_raw_path: Optional[Path] = None) -> SiteHealthReport:
    report = SiteHealthReport(url=url)
    try:
        client = httpx.Client(verify=True, follow_redirects=True, timeout=DEFAULT_TIMEOUT)
        client.headers.update({"User-Agent": "Mozilla/5.0 (compatible; ProcureBot/1.0)"})
        resp = client.get(url)
        client.close()
        resp.raise_for_status()
        report.http_status_ok = True
    except httpx.HTTPError as e:
        report.notes.append(f"Request failed: {e}")
        log.error("site_health_request_failed", url=url, error=str(e))
        return report

    html_text = resp.text
    report.content_length = len(html_text)

    if save_raw_path:
        save_raw_path.parent.mkdir(parents=True, exist_ok=True)
        save_raw_path.write_text(html_text, encoding="utf-8")

    if check_maintenance(html_text):
        report.hit_maintenance = True
        report.notes.append("e-GP maintenance banner detected — page returns placeholder, not real content")
        log.warning("site_health_maintenance_detected", url=url)
        return report

    soup = BeautifulSoup(html_text, "html.parser")

    links = soup.find_all("a")
    report.link_texts = sorted({a.get_text(strip=True) for a in links if a.get_text(strip=True)})
    report.link_hrefs_sample = [a.get("href") for a in links[:40] if a.get("href")]

    budget_keywords = ["development", "revenue", "own fund", "db", "rb", "of", "budget"]
    for a in links:
        text_lower = a.get_text(strip=True).lower()
        if any(kw in text_lower for kw in budget_keywords):
            report.budget_type_candidates.append({
                "text": a.get_text(strip=True),
                "href": a.get("href"),
            })

    tables = soup.find_all("table")
    report.table_count = len(tables)
    report.table_row_counts = [len(t.find_all("tr")) for t in tables]

    inputs = soup.find_all(["input", "select"])
    report.form_field_names = sorted({i.get("name") for i in inputs if i.get("name")})

    if report.table_count == 0:
        report.notes.append("No <table> elements found — page may use JS-rendered grids or layout changed")
    if not report.budget_type_candidates:
        report.notes.append("No budget-type links found ('DB'/'RB'/'OF' keywords absent) — exact-text selectors likely stale")

    log.info("site_health_done", url=url, tables=report.table_count, links=len(report.link_texts))
    return report
