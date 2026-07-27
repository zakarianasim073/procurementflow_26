from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..framework.logger import get_logger
from ..framework.validator import DataValidator
from .base import BaseCrawler, CrawlContext

log = get_logger("crawler.plugin_loader")


class ConfigDrivenCrawler(BaseCrawler):
    def __init__(self, yaml_config: Dict[str, Any], **kwargs):
        self.yaml = yaml_config
        self._name = yaml_config.get("name", "config_driven")
        super().__init__(config=yaml_config.get("config", {}), **kwargs)
        self._search_url = yaml_config.get("search", {}).get("url", "")
        self._list_selector = yaml_config.get("list", {}).get("selector", "")
        self._list_item_selector = yaml_config.get("list", {}).get("item_selector", "tr")
        self._detail_url_template = yaml_config.get("detail", {}).get("url_template", "")
        self._detail_url_field = yaml_config.get("detail", {}).get("url_field", "href")
        self._field_mappings = yaml_config.get("fields", {})
        self._pagination_config = yaml_config.get("pagination", {})
        self._document_config = yaml_config.get("documents", {})
        self._validation_config = yaml_config.get("validation", {})

    async def search(self):
        nav = self.get_navigator(self._get_page())
        await nav.goto(self._search_url)

    async def parse_list(self) -> List[Dict[str, Any]]:
        from ..framework.extractor import extract_table_rows, extract_links
        page = self._get_page()
        rows = await extract_table_rows(page, self._list_item_selector)
        items = []
        for row in rows:
            item = {"_raw_row": row}
            for field_name, mapping in self._field_mappings.items():
                col_idx = mapping.get("column", None)
                if col_idx is not None and col_idx < len(row):
                    item[field_name] = row[col_idx]
            items.append(item)
        return items

    async def parse_details(self, item: Dict[str, Any]) -> Dict[str, Any]:
        from ..framework.extractor import extract_label_value_map
        page = self._get_page()
        kv = await extract_label_value_map(page)
        for field_name, mapping in self._field_mappings.items():
            sources = mapping.get("sources", [field_name])
            if field_name not in item or not item.get(field_name):
                for src in sources:
                    val = None
                    for k, v in kv.items():
                        if k.lower().startswith(src.lower()):
                            val = v
                            break
                    if val:
                        item[field_name] = val
                        break
        item["_raw_kv"] = kv
        return item

    async def download_documents(self, item: Dict[str, Any]) -> Dict[str, Any]:
        doc_url_field = self._document_config.get("url_field")
        doc_type = self._document_config.get("type", "pdf")
        if doc_url_field and doc_url_field in item:
            url = item[doc_url_field]
            if self.downloader:
                path = await self.downloader.download(url, sub_dir=str(item.get("id", "unknown")), referer=self._search_url)
                if path:
                    item["_downloaded_path"] = str(path)
                    item["_downloaded_type"] = doc_type
        return item

    async def next_page(self) -> bool:
        from ..framework.pagination import PaginationHandler
        page = self._get_page()
        btn = await PaginationHandler.find_next_button(page)
        if btn:
            from playwright.async_api import expect
            try:
                await page.click(btn)
                await page.wait_for_load_state("networkidle")
                return True
            except Exception:
                return False
        return False

    def _get_page(self):
        return self._page_pool[0] if self._page_pool else None

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value


def load_plugin(name: str) -> Optional[BaseCrawler]:
    """Return an instantiated crawler for *name*, auto-discovering plugins if needed."""
    from .registry import discover_plugins, get
    discover_plugins()
    cls = get(name)
    if cls is None:
        log.warning("plugin_not_found", name=name)
        return None
    return cls()


def load_plugin_from_yaml(yaml_path: Path) -> Optional[ConfigDrivenCrawler]:
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not config:
            return None

        crawler = ConfigDrivenCrawler(yaml_config=config)
        return crawler
    except Exception as e:
        log.error("yaml_load_failed", path=str(yaml_path), error=e)
        return None


def discover_yaml_configs(config_dir: Path) -> Dict[str, ConfigDrivenCrawler]:
    crawlers = {}
    if not config_dir.exists():
        log.warning("config_dir_not_found", path=str(config_dir))
        return crawlers
    for yaml_file in config_dir.glob("*.yaml"):
        crawler = load_plugin_from_yaml(yaml_file)
        if crawler:
            crawlers[crawler.name] = crawler
            log.info("yaml_plugin_loaded", name=crawler.name, path=str(yaml_file))
    return crawlers
