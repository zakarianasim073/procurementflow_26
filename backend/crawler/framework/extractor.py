from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Pattern

from playwright.async_api import Page


async def extract_label_value_map(page: Page) -> Dict[str, str]:
    body_text = await page.inner_text("body")
    lines = [l.strip() for l in body_text.split("\n") if l.strip()]
    kv = {}
    pattern = re.compile(r"^(.+?)\s*:\s*(.*)$")
    i = 0
    while i < len(lines):
        line = lines[i]
        match = pattern.match(line)
        if match:
            label, value = match.group(1).strip(), match.group(2).strip()
            if not value and i + 1 < len(lines) and not pattern.match(lines[i + 1]):
                value = lines[i + 1].strip()
                i += 1
            kv[label] = value
        i += 1
    return kv


async def extract_label_value_map_v2(page: Page) -> Dict[str, str]:
    try:
        tables = await page.query_selector_all("table")
        kv = {}
        for table in tables:
            rows = await table.query_selector_all("tr")
            for row in rows:
                cells = await row.query_selector_all("td, th")
                cell_texts = [((await c.inner_text()).strip()) for c in cells]
                cleaned = [re.sub(r"\s+", " ", t) for t in cell_texts if t.strip()]
                for i, text in enumerate(cleaned):
                    if ":" in text:
                        parts = text.split(":", 1)
                        label = parts[0].strip()
                        value = parts[1].strip()
                        if label and value:
                            kv[label] = value
                    elif i + 1 < len(cleaned) and not cleaned[i + 1].startswith(":"):
                        if cleaned[i + 1].strip():
                            kv[text] = cleaned[i + 1].strip()
        return kv
    except Exception:
        return await extract_label_value_map(page)


def get_field(kv: Dict[str, Any], *possible_labels: str, default: Optional[str] = None) -> Optional[str]:
    for label in possible_labels:
        for key in kv:
            if key.lower().startswith(label.lower()):
                return kv[key]
    return default


def get_field_regex(kv: Dict[str, Any], pattern: Pattern) -> Optional[str]:
    for key in kv:
        if pattern.search(key):
            return kv[key]
    return None


async def extract_table_rows(page: Page, table_selector: str = "table") -> List[List[str]]:
    rows = await page.query_selector_all(f"{table_selector} tr")
    result = []
    for row in rows:
        cells = await row.query_selector_all("td, th")
        texts = [((await c.inner_text()).strip()) for c in cells]
        if any(t.strip() for t in texts):
            result.append(texts)
    return result


async def extract_table_as_dicts(page: Page, table_selector: str = "table") -> List[Dict[str, str]]:
    rows = await page.query_selector_all(f"{table_selector} tr")
    if not rows:
        return []
    header_cells = await rows[0].query_selector_all("td, th")
    headers = [((await c.inner_text()).strip()) for c in header_cells]
    result = []
    for row in rows[1:]:
        cells = await row.query_selector_all("td, th")
        texts = [((await c.inner_text()).strip()) for c in cells]
        if any(t.strip() for t in texts):
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(texts):
                    row_dict[header] = texts[i]
            result.append(row_dict)
    return result


async def extract_links(page: Page, contains: Optional[str] = None) -> List[Dict[str, str]]:
    links = await page.query_selector_all("a")
    out = []
    for link in links:
        href = await link.get_attribute("href")
        text = (await link.inner_text()).strip()
        if href and (not contains or contains in href):
            out.append({"href": href, "text": text})
    return out


async def extract_elements_by_selector(
    page: Page,
    selector: str,
    attribute: Optional[str] = None,
) -> List[str]:
    elements = await page.query_selector_all(selector)
    result = []
    for el in elements:
        if attribute:
            val = await el.get_attribute(attribute)
            if val:
                result.append(val.strip())
        else:
            val = (await el.inner_text()).strip()
            if val:
                result.append(val)
    return result


async def extract_json_from_script(page: Page, script_id_contains: str = "data") -> Optional[dict]:
    scripts = await page.query_selector_all("script")
    for script in scripts:
        src = await script.get_attribute("src") or ""
        if script_id_contains in src:
            continue
        content = await script.inner_text()
        if content.strip():
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError:
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith(("{", "[")):
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            pass
    return None


async def extract_meta_tags(page: Page) -> Dict[str, str]:
    metas = await page.query_selector_all("meta")
    result = {}
    for meta in metas:
        name = await meta.get_attribute("name") or await meta.get_attribute("property") or ""
        content = await meta.get_attribute("content") or ""
        if name and content:
            result[name] = content
    return result
