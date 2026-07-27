from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..framework.config import settings
from ..framework.logger import get_logger
from ..plugins.registry import list_plugins
from ..workers.orchestrator import CrawlerOrchestrator

log = get_logger("crawler.scheduler")


class CrawlSchedule:
    def __init__(self, name: str, cron: str, plugins: List[str], config: Optional[dict] = None):
        self.name = name
        self.cron = cron
        self.plugins = plugins
        self.config = config or {}
        self.last_run: Optional[str] = None


class CrawlerScheduler:
    def __init__(self, orchestrator: CrawlerOrchestrator):
        self.orchestrator = orchestrator
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._schedules: List[CrawlSchedule] = []
        self._state_file = Path("output/scheduler_state.json")

    def add_schedule(self, schedule: CrawlSchedule):
        self._schedules.append(schedule)

    def load_default_schedules(self):
        self._schedules = [
            CrawlSchedule(
                name="daily_tenders",
                cron="0 */6 * * *",
                plugins=["tender", "award"],
                config={"mode": "incremental", "max_pages": 20},
            ),
            CrawlSchedule(
                name="daily_full",
                cron="0 2 * * *",
                plugins=["tender", "award", "experience", "app", "debarment"],
                config={"mode": "incremental", "max_pages": 50},
            ),
            CrawlSchedule(
                name="weekly_verify",
                cron="0 6 * * 1",
                plugins=["tender", "award"],
                config={"mode": "verify", "max_pages": 100},
            ),
        ]

    async def start(self):
        self._running = True
        self.load_default_schedules()
        self._task = asyncio.create_task(self._scheduler_loop())
        log.info("scheduler_started", schedules=[s.name for s in self._schedules])

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._save_state()
        log.info("scheduler_stopped")

    async def _scheduler_loop(self):
        while self._running:
            now = datetime.now(timezone.utc)
            for schedule in self._schedules:
                if self._should_run(schedule, now):
                    log.info("schedule_triggered", name=schedule.name, plugins=schedule.plugins)
                    try:
                        results = await self.orchestrator.run_all(
                            plugin_names=schedule.plugins,
                            configs={p: schedule.config for p in schedule.plugins},
                        )
                        for plugin, result in results.items():
                            log.info(
                                "schedule_plugin_complete",
                                name=schedule.name,
                                plugin=plugin,
                                status=result.status,
                                items=result.items_done,
                            )
                        schedule.last_run = now.isoformat()
                        self._save_state()
                    except Exception as e:
                        log.error("schedule_run_failed", name=schedule.name, error=e)

            await asyncio.sleep(60)

    def _should_run(self, schedule: CrawlSchedule, now: datetime) -> bool:
        now_str = now.strftime("%H:%M")
        scheduled_time = schedule.cron.split(" ")[1] + ":" + schedule.cron.split(" ")[0]
        scheduled_minutes = int(schedule.cron.split(" ")[0])
        scheduled_hour = int(schedule.cron.split(" ")[1])

        if schedule.last_run:
            last = datetime.fromisoformat(schedule.last_run)
            if (now - last).total_seconds() < 3600:
                return False

        if now.hour == scheduled_hour and now.minute == scheduled_minutes:
            return True

        return False

    def _save_state(self):
        try:
            state = {
                s.name: {"last_run": s.last_run}
                for s in self._schedules
            }
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(state, indent=2))
        except Exception as e:
            log.warning("state_save_failed", error=e)

    def _load_state(self):
        if self._state_file.exists():
            try:
                state = json.loads(self._state_file.read_text())
                for s in self._schedules:
                    if s.name in state:
                        s.last_run = state[s.name].get("last_run")
            except (json.JSONDecodeError, IOError) as e:
                log.warning("state_load_failed", error=e)

    async def run_now(self, plugins: List[str], config: Optional[dict] = None):
        return await self.orchestrator.run_all(
            plugin_names=plugins,
            configs={p: config or {} for p in plugins},
        )

    async def run_single(self, plugin: str, config: Optional[dict] = None):
        return await self.orchestrator.run_plugin(plugin, config=config)
