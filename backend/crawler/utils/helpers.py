from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


def normalize_package_no(package_no: Optional[str]) -> Optional[str]:
    if not package_no:
        return None
    return re.sub(r"[\s\-_/]+", "", package_no.upper().strip()).replace(" ", "")


def extract_tender_id(url_or_text: str) -> Optional[str]:
    patterns = [
        re.compile(r"(?:[?&]|^)id[=_](\d+)"),
        re.compile(r"tender[=_/]?id[=_]?(\d+)", re.I),
        re.compile(r"/(\d{6,9})(?:\?|/|$)"),
        re.compile(r"ViewTender\.jsp.*?id=(\d+)"),
    ]
    for pattern in patterns:
        m = pattern.search(url_or_text)
        if m:
            return m.group(1)
    return None


def extract_pkg_id(url: str) -> Optional[str]:
    m = re.search(r"pkgId[=_]?(\d+)", url)
    return m.group(1) if m else None


def extract_app_id(text: str) -> Optional[str]:
    m = re.search(r"APP\s*ID\s*:?\s*(\d+)", text, re.I)
    return m.group(1) if m else None


def clean_bdt_amount(value: str) -> Optional[float]:
    if not value:
        return None
    cleaned = re.sub(r"(?i)(?:tk\.?\s*|taka\s*|bdt\s*|b\.?d\.?t?\s*)", "", value)
    cleaned = cleaned.replace(",", "")
    digits_and_dots = re.findall(r"\d+\.?\d*", cleaned)
    if not digits_and_dots:
        return None
    combined = "".join(digits_and_dots)
    if combined.count(".") > 1:
        combined = combined.replace(".", "", combined.count(".") - 1)
    try:
        return float(combined)
    except (ValueError, TypeError):
        return None


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


def parse_fiscal_year(year_str: str) -> Optional[str]:
    m = re.match(r"(\d{4})-(\d{2,4})", year_str.strip())
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"(\d{4})(\d{4})", year_str.strip())
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return year_str.strip()


def get_checkpoint(checkpoint_dir: Path, name: str) -> Dict[str, Any]:
    path = checkpoint_dir / f"{name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_checkpoint(checkpoint_dir: Path, name: str, data: Dict[str, Any]):
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    path = checkpoint_dir / f"{name}.json"
    path.write_text(json.dumps(data, default=str))


def filter_works_only(record: Dict[str, Any]) -> bool:
    category = record.get("category", "")
    if isinstance(category, str):
        return category.lower() == "works"
    return False


def chunk_list(items: List[Any], chunk_size: int = 100) -> List[List[Any]]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def safe_filename(name: str, max_length: int = 100) -> str:
    safe = re.sub(r"[^\w\s-_.]", "", name).strip()
    if len(safe) > max_length:
        base, ext = re.match(r"^(.*?)(\.[^.]+)?$", safe).groups()
        safe = base[:max_length - (len(ext) if ext else 0)] + (ext or "")
    return safe


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def md5_hash(data: Any) -> str:
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(content.encode()).hexdigest()


def extract_table_from_html(html: str) -> List[List[str]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(cells)
    return rows
