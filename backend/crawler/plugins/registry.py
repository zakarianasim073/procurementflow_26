from __future__ import annotations

import importlib
from typing import Dict, List, Optional, Type

from .base import BaseCrawler

_plugin_registry: Dict[str, Type[BaseCrawler]] = {}
_plugin_manifests: Dict[str, object] = {}


def register(name: str):
    def decorator(crawler_class: Type[BaseCrawler]) -> Type[BaseCrawler]:
        _plugin_registry[name] = crawler_class
        return crawler_class
    return decorator


def unregister(name: str):
    _plugin_registry.pop(name, None)


def get(name: str) -> Optional[Type[BaseCrawler]]:
    return _plugin_registry.get(name)


def list_plugins() -> List[str]:
    return list(_plugin_registry.keys())


def get_all() -> Dict[str, Type[BaseCrawler]]:
    return dict(_plugin_registry)


# Alias used by CrawlImportService
get_registered_crawlers = get_all


def discover_plugins():
    from ..framework.logger import get_logger
    log = get_logger("crawler.registry")

    if _plugin_registry:
        log.info("plugins_already_discovered", count=len(_plugin_registry))
        return

    builtin_plugins = [
        ("app", "APPCrawler", "crawler.plugins.app.app_crawler", "backend.crawler.plugins.app.app_crawler"),
        ("tender", "TenderCrawler", "crawler.plugins.tender.tender_crawler", "backend.crawler.plugins.tender.tender_crawler"),
        ("award", "AwardCrawler", "crawler.plugins.award.award_crawler", "backend.crawler.plugins.award.award_crawler"),
        ("experience", "ExperienceCrawler", "crawler.plugins.experience.experience_crawler", "backend.crawler.plugins.experience.experience_crawler"),
        ("debarment", "DebarmentCrawler", "crawler.plugins.debarment.debarment_crawler", "backend.crawler.plugins.debarment.debarment_crawler"),
        ("offline_tender", "OfflineTenderCrawler", "crawler.plugins.tender.offline_crawler", "backend.crawler.plugins.tender.offline_crawler"),
        ("offline_award", "OfflineAwardCrawler", "crawler.plugins.award.offline_award_crawler", "backend.crawler.plugins.award.offline_award_crawler"),
        ("documents", "DocumentCrawler", "crawler.plugins.documents.document_crawler", "backend.crawler.plugins.documents.document_crawler"),
    ]

    for plugin_name, class_name, *paths in builtin_plugins:
        module = None
        for path in paths:
            try:
                module = importlib.import_module(path)
                break
            except ModuleNotFoundError:
                continue
        if module is None:
            log.warning("plugin_discovery_failed", plugin=plugin_name, paths=paths)
            continue
        cls = getattr(module, class_name, None)
        if cls is None:
            log.warning("class_not_found", plugin=plugin_name, class_name=class_name)
            continue
        _plugin_registry[plugin_name] = cls
        log.info("plugin_registered", plugin=plugin_name)


def discover_plugins_from_yaml():
    """Scan plugin.yaml manifests in each plugin directory (auto-discovery)."""
    from ..framework.logger import get_logger
    from ..framework.plugin_loader import PluginAutoLoader
    log = get_logger("crawler.registry")
    try:
        loader = PluginAutoLoader()
        manifests = loader.discover_all()
        for name, manifest in manifests.items():
            errors = loader.validate_schema(manifest)
            if errors:
                log.warning("plugin_manifest_invalid", name=name, errors=errors)
                continue
            _plugin_manifests[name] = manifest
            log.info("plugin_manifest_registered", name=name, version=manifest.version)
    except Exception as e:
        log.warning("plugin_yaml_discovery_failed", error=str(e))


def get_manifest(plugin_name: str):
    return _plugin_manifests.get(plugin_name)


def list_manifests() -> dict:
    return {k: v.to_dict() for k, v in _plugin_manifests.items()}
