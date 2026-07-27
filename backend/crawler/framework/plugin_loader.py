from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..framework.logger import get_logger

log = get_logger("crawler.plugin_loader")


class PluginManifest:
    """Versioned plugin metadata parsed from a plugin.yaml manifest."""

    def __init__(self, name: str, version: str, module: str, class_name: str,
                 description: str = "", author: str = "procureflow", config: Dict[str, Any] = None):
        self.name = name
        self.version = version
        self.module = module
        self.class_name = class_name
        self.description = description
        self.author = author
        self.config = config or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "module": self.module,
            "class_name": self.class_name,
            "description": self.description,
            "author": self.author,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "0.0.0"),
            module=data.get("module", ""),
            class_name=data.get("class", ""),
            description=data.get("description", ""),
            author=data.get("author", "procureflow"),
            config=data.get("config", {}),
        )


class PluginAutoLoader:
    """Discovers crawler plugins via plugin.yaml manifests in plugin directories."""

    def __init__(self, plugins_root: Optional[Path] = None):
        self.plugins_root = plugins_root or Path(__file__).parent.parent / "plugins"

    def discover_all(self) -> Dict[str, PluginManifest]:
        """Scan all plugin directories for plugin.yaml manifests."""
        manifests: Dict[str, PluginManifest] = {}
        if not self.plugins_root.exists():
            log.warning("plugins_root_not_found", path=str(self.plugins_root))
            return manifests

        for plugin_dir in sorted(self.plugins_root.iterdir()):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("__"):
                continue
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data:
                    continue
                manifest = PluginManifest.from_dict(data)
                manifests[manifest.name] = manifest
                log.info("plugin_manifest_loaded", name=manifest.name,
                         version=manifest.version, module=manifest.module)
            except Exception as e:
                log.error("plugin_manifest_parse_failed", path=str(manifest_path), error=str(e))
        return manifests

    def get_config(self, plugin_name: str) -> Optional[PluginManifest]:
        return self.discover_all().get(plugin_name)

    def validate_schema(self, manifest: PluginManifest) -> List[str]:
        errors = []
        if not manifest.name:
            errors.append("name is required")
        if not manifest.module:
            errors.append("module is required")
        if not manifest.class_name:
            errors.append("class (class_name) is required")
        return errors
