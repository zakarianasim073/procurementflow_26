from __future__ import annotations

import asyncio
import sys
from typing import List, Optional

from .framework.config import settings
from .framework.logger import get_logger
from .plugins.registry import discover_plugins, list_plugins
from .plugins.loader import discover_yaml_configs
from .scheduler.scheduler import CrawlerScheduler
from .workers.orchestrator import CrawlerOrchestrator

log = get_logger("crawler.runner")


async def run_plugins(
    plugins: Optional[List[str]] = None,
    configs: Optional[dict] = None,
    use_scheduler: bool = False,
):
    settings.ensure_dirs()
    discover_plugins()
    from .plugins.registry import discover_plugins_from_yaml
    discover_plugins_from_yaml()

    yaml_plugins = discover_yaml_configs(settings.output_dir.parent.parent / "config")
    for name, yaml_crawler in yaml_plugins.items():
        log.info("yaml_plugin_available", name=name)

    orchestrator = CrawlerOrchestrator()
    try:
        await orchestrator.start()

        if use_scheduler:
            scheduler = CrawlerScheduler(orchestrator)
            await scheduler.start()
            log.info("scheduler_running")
            try:
                while True:
                    await asyncio.sleep(60)
            except KeyboardInterrupt:
                log.info("shutdown_requested")
                await scheduler.stop()
        else:
            target_plugins = plugins or list_plugins()
            log.info("running_plugins", plugins=target_plugins)
            results = await orchestrator.run_all(
                plugin_names=target_plugins,
                configs=configs,
            )
            for name, result in results.items():
                status_emoji = "OK" if result.status == "success" else "FAIL"
                log.info(
                    "plugin_result",
                    plugin=name,
                    status=result.status,
                    pages=result.pages_done,
                    items=result.items_done,
                    skipped=result.items_skipped,
                    failed=result.items_failed,
                    error=result.error,
                )
    finally:
        await orchestrator.stop()


async def run_single_plugin(plugin_name: str, config: Optional[dict] = None):
    settings.ensure_dirs()
    discover_plugins()
    from .plugins.registry import discover_plugins_from_yaml
    discover_plugins_from_yaml()

    orchestrator = CrawlerOrchestrator()
    result = None
    try:
        await orchestrator.start()
        result = await orchestrator.run_plugin(plugin_name, config=config)
        log.info(
            "single_plugin_result",
            plugin=plugin_name,
            status=result.status,
            pages=result.pages_done,
            items=result.items_done,
            error=result.error,
        )
    finally:
        await orchestrator.stop()
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ProcureFlow Enterprise Crawler Framework")
    parser.add_argument("--plugins", "-p", type=str, default=None,
                        help="Comma-separated plugin names to run")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="Max pages per plugin")
    parser.add_argument("--mode", type=str, default="incremental",
                        choices=["incremental", "full", "verify", "resume"],
                        help="Crawl mode")
    parser.add_argument("--scheduler", "-s", action="store_true",
                        help="Run scheduler mode (continuous)")
    parser.add_argument("--list-plugins", "-l", action="store_true",
                        help="List available plugins and exit")
    parser.add_argument("--single", type=str, default=None,
                        help="Run a single plugin by name")
    args = parser.parse_args()

    if args.list_plugins:
        discover_plugins()
        print("Available plugins:")
        for name in sorted(list_plugins()):
            print(f"  - {name}")
        return

    config = {}
    if args.max_pages:
        config["max_pages"] = args.max_pages
    if args.mode:
        config["mode"] = args.mode

    if args.single:
        asyncio.run(run_single_plugin(args.single, config=config))
        return

    plugins = args.plugins.split(",") if args.plugins else None
    asyncio.run(run_plugins(plugins=plugins, configs={p: config for p in (plugins or [])} if config else None))


if __name__ == "__main__":
    main()
