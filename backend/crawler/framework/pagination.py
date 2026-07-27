from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from playwright.async_api import Page

from .logger import get_logger

log = get_logger("crawler.pagination")


@dataclass
class PaginationState:
    current_page: int = 1
    total_pages: Optional[int] = None
    total_items: Optional[int] = None
    per_page: int = 20
    urls_visited: set = field(default_factory=set)
    items_seen: set = field(default_factory=set)
    consecutive_empty: int = 0
    max_consecutive_empty: int = 3
    is_exhausted: bool = False
    page_param: str = "pageNo"
    url_template: Optional[str] = None
    param_pattern: Optional[re.Pattern] = None

    def mark_visited(self, url: str):
        self.urls_visited.add(url)

    def was_visited(self, url: str) -> bool:
        return url in self.urls_visited

    def record_items(self, item_ids: List[str]):
        new_items = [i for i in item_ids if i not in self.items_seen]
        self.items_seen.update(item_ids)
        if not new_items:
            self.consecutive_empty += 1
        else:
            self.consecutive_empty = 0
        if self.consecutive_empty >= self.max_consecutive_empty:
            self.is_exhausted = True

    def next_page_url(self, base_url: str) -> Optional[str]:
        if self.is_exhausted:
            return None
        if self.total_pages and self.current_page >= self.total_pages:
            self.is_exhausted = True
            return None
        self.current_page += 1
        if self.url_template:
            return self.url_template.format(page=self.current_page)
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{self.page_param}={self.current_page}"


class PaginationHandler:
    COMMON_PATTERNS = [
        (re.compile(r"page[=_ ]?(\d+)", re.I), lambda m: int(m.group(1))),
        (re.compile(r"p[=_ ]?(\d+)", re.I), lambda m: int(m.group(1))),
        (re.compile(r"pageNo[=_ ]?(\d+)", re.I), lambda m: int(m.group(1))),
        (re.compile(r"offset[=_ ]?(\d+)", re.I), lambda m: int(m.group(1))),
    ]

    BUTTON_SELECTORS = [
        "a:has-text('Next')",
        "a:has-text('next')",
        "a:has-text('→')",
        "a:has-text('>')",
        "a.next",
        "button:has-text('Next')",
        ".pagination .next a",
        "[aria-label='Next']",
    ]

    @staticmethod
    def detect_page_param(url: str) -> Optional[Tuple[str, int]]:
        for pattern, extractor in PaginationHandler.COMMON_PATTERNS:
            m = pattern.search(url)
            if m:
                try:
                    return (pattern.pattern, extractor(m))
                except (ValueError, IndexError):
                    pass
        return None

    @staticmethod
    def make_next_url(base_url: str, current_page: int) -> str:
        param_patterns = [
            (re.compile(r"(page[=_ ]?)(\d+)", re.I)),
            (re.compile(r"(p[=_ ]?)(\d+)", re.I)),
            (re.compile(r"(pageNo[=_ ]?)(\d+)", re.I)),
        ]
        for pattern in param_patterns:
            m = pattern.search(base_url)
            if m:
                prefix = m.group(1)
                return base_url[:m.start(2)] + str(current_page + 1) + base_url[m.end(2):]
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}pageNo={current_page + 1}"

    @staticmethod
    async def find_next_button(page: Page) -> Optional[str]:
        for selector in PaginationHandler.BUTTON_SELECTORS:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    href = await btn.get_attribute("href")
                    if href:
                        return href
                    is_disabled = await btn.get_attribute("disabled")
                    class_name = await btn.get_attribute("class") or ""
                    if not is_disabled and "disabled" not in class_name:
                        return selector
            except Exception:
                continue
        return None

    @staticmethod
    async def get_total_pages(page: Page) -> Optional[int]:
        patterns = [
            re.compile(r"Page\s+(\d+)\s+of\s+(\d+)", re.I),
            re.compile(r"(\d+)\s*/\s*(\d+)\s*Pages?", re.I),
            re.compile(r"Showing.*?(\d+)\s*-\s*(\d+)\s*of\s*(\d+)", re.I),
        ]
        try:
            body = await page.inner_text("body")
            for pattern in patterns:
                m = pattern.search(body)
                if m:
                    if len(m.groups()) >= 2:
                        try:
                            return int(m.group(2))
                        except (ValueError, IndexError):
                            pass
        except Exception:
            pass
        return None

    @staticmethod
    async def get_total_items(page: Page) -> Optional[int]:
        patterns = [
            re.compile(r"Total\s*(?:Record|Item|Result)s?\s*:?\s*(\d+)", re.I),
            re.compile(r"(\d+)\s*(?:Record|Item|Result)s?\s*found", re.I),
            re.compile(r"Showing.*?of\s*(\d+)\s*(?:entries|results|items)", re.I),
        ]
        try:
            body = await page.inner_text("body")
            for pattern in patterns:
                m = pattern.search(body)
                if m:
                    try:
                        return int(m.group(1))
                    except (ValueError, IndexError):
                        pass
        except Exception:
            pass
        return None
