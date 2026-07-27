#!/usr/bin/env python
"""
Multi-plugin parallel crawler with configurable pages and change detection.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Tuple

from .run_all import run_single_plugin


def run_plugin_sync(plugin_name: str, config: Dict[str, Any]):
    """Run a single plugin synchronously by creating a new event loop."""
    return asyncio.run(run_single_plugin(plugin_name, config))


def main():
    """
    Run the requested crawlers in parallel.
    
    This script runs all 4 crawler types with their specified page limits:
    - tender: Runs all pages without limit
    - award: 300-600 pages with change detection
    - experience: 200-400 pages with change detection  
    - debarment: 50-100 pages with change detection
    """
    configs = {
        "tender": {
            "mode": "incremental",
            "max_pages": -1,  # -1 means unlimited pages
            "detect_changes": True,
            "search_mode": "listings",
            "view_types": ["Live"],
            "page_size": 50,
            "timeout": 70.0,
        },
        "award": {
            "mode": "incremental",
            "max_pages": 450,  # midpoint of 300-600
            "page_size": 50,
            "timeout": 70.0,
            "rate_limit": 1.0,
            "extract_details": True,
            "detect_changes": True,
        },
        "experience": {
            "mode": "incremental",
            "max_pages": 300,  # midpoint of 200-400
            "page_size": 50,
            "timeout": 70.0,
            "rate_limit": 2.0,
            "detect_changes": True,
        },
        "debarment": {
            "mode": "incremental",
            "max_pages": 75,  # midpoint of 50-100
            "page_size": 50,
            "timeout": 70.0,
            "rate_limit": 2.0,
            "detect_changes": True,
        },
    }

    print("Starting multi-plugin parallel crawler...")
    print("Configurations:")
    for plugin, config in configs.items():
        max_pages = config["max_pages"] if config["max_pages"] != -1 else "unlimited"
        print(f"  {plugin}: max_pages={max_pages}, detect_changes={config['detect_changes']}")
    print()

    # Run plugins in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_plugin = {
            executor.submit(run_plugin_sync, plugin, config): plugin
            for plugin, config in configs.items()
        }

        for future in as_completed(future_to_plugin):
            plugin = future_to_plugin[future]
            try:
                result = future.result()
                status = "OK" if result.status == "success" else "FAIL"
                print(f"[{status}] {plugin}: completed - items_saved={result.items_done}, pages={result.pages_done}")
            except Exception as e:
                print(f"[FAIL] {plugin}: failed with error: {e}")

    print("\nAll crawlers completed!")


if __name__ == "__main__":
    main()
