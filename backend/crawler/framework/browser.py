from __future__ import annotations

import asyncio
import os
import random
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
    TimeoutError as PWTimeout,
    Error as PWError,
)

from .config import settings
from .logger import get_logger
from .metrics import record_error, record_captcha

log = get_logger("crawler.browser")

STEALTH_SCRIPT = """
// Override navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Override chrome.runtime
window.chrome = { runtime: {} };

// Override permissions
const originalQuery = navigator.permissions.query;
navigator.permissions.query = (params) => (
    params.name === 'notifications'
        ? Promise.resolve({ state: 'denied' })
        : originalQuery(params)
);

// Override plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// Override webgl vendor/renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, param);
};
"""


class BrowserManager:
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._available_contexts: asyncio.Queue[BrowserContext] = asyncio.Queue()
        self._busy_contexts: set = set()
        self._max_contexts: int = settings.browser_max_contexts
        self._sem: asyncio.Semaphore = asyncio.Semaphore(settings.browser_max_contexts)
        self._running: bool = False
        self._recovery_task: Optional[asyncio.Task] = None
        self._screenshot_dir: Optional[Path] = None

    async def start(self):
        log.info("browser_starting", max_contexts=self._max_contexts)
        try:
            self._playwright = await async_playwright().start()

            launch_args = [
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-blink-features=AutomationControlled",
                f"--window-size={settings.browser_viewport_width},{settings.browser_viewport_height}",
            ]

            launch_kwargs: Dict[str, Any] = {
                "headless": settings.browser_headless,
                "args": launch_args,
            }

            if settings.proxy_enabled and settings.proxy_url:
                launch_kwargs["proxy"] = {"server": settings.proxy_url}
                log.info("browser_proxy_enabled", proxy=settings.proxy_url)

            self._browser = await self._playwright.chromium.launch(**launch_kwargs)

            for i in range(self._max_contexts):
                ctx = await self._create_context()
                await self._available_contexts.put(ctx)
            self._running = True
            self._recovery_task = asyncio.create_task(self._health_check_loop())
            log.info("browser_started", contexts=self._max_contexts)
        except Exception as e:
            log.error("browser_start_failed", error=e)
            raise

    async def _random_viewport(self) -> Dict[str, int]:
        w = settings.browser_viewport_width
        h = settings.browser_viewport_height
        if settings.proxy_enabled:
            w += random.randint(-20, 20)
            h += random.randint(-20, 20)
        return {"width": w, "height": h}

    async def _create_context(self) -> BrowserContext:
        viewport = await self._random_viewport()
        ctx_kwargs: Dict[str, Any] = {
            "viewport": viewport,
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "locale": "en-US",
            "timezone_id": "Asia/Dhaka",
            "permissions": [],
            "geolocation": {"latitude": 23.8103, "longitude": 90.4125},
            "no_viewport": False,
        }

        if settings.browser_stealth:
            ctx_kwargs["color_scheme"] = "light"

        ctx = await self._browser.new_context(**ctx_kwargs)
        ctx.set_default_timeout(settings.browser_timeout_ms)
        ctx.set_default_navigation_timeout(settings.browser_navigation_timeout_ms)

        if settings.browser_stealth:
            await ctx.add_init_script(STEALTH_SCRIPT)

        return ctx

    async def get_context(self) -> BrowserContext:
        await self._sem.acquire()
        try:
            ctx = await asyncio.wait_for(
                self._available_contexts.get(), timeout=30.0
            )
            self._busy_contexts.add(id(ctx))
            return ctx
        except asyncio.TimeoutError:
            self._sem.release()
            raise RuntimeError("No available browser contexts after 30s timeout")

    async def release_context(self, context: BrowserContext):
        ctx_id = id(context)
        self._busy_contexts.discard(ctx_id)
        try:
            await context.clear_cookies()
            await self._available_contexts.put(context)
        except Exception as e:
            log.warning("context_release_failed, creating replacement", error=e)
            try:
                await context.close()
            except Exception:
                pass
            new_ctx = await self._create_context()
            await self._available_contexts.put(new_ctx)
        finally:
            self._sem.release()

    async def restart_context(self, context: BrowserContext) -> BrowserContext:
        ctx_id = id(context)
        self._busy_contexts.discard(ctx_id)
        try:
            await context.close()
        except Exception:
            pass
        new_ctx = await self._create_context()
        await self._available_contexts.put(new_ctx)
        self._sem.release()
        return await self.get_context()

    async def screenshot(
        self,
        page: Page,
        name: str = "screenshot",
        full_page: bool = True,
    ) -> Optional[str]:
        if not self._screenshot_dir:
            self._screenshot_dir = settings.output_dir / "screenshots"
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(self._screenshot_dir / f"{name}_{ts}.png")
        try:
            await page.screenshot(path=path, full_page=full_page)
            return path
        except Exception as e:
            log.warning("screenshot_failed", name=name, error=str(e))
            return None

    async def new_page_with_retry(
        self,
        context: BrowserContext,
        url: str,
        retries: int = 3,
    ) -> Tuple[Optional[Page], Optional[str]]:
        last_error = None
        for attempt in range(retries):
            try:
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded")
                return page, None
            except Exception as e:
                last_error = str(e)
                log.warning(
                    "page_navigation_retry",
                    url=url[:100],
                    attempt=attempt + 1,
                    error=last_error,
                )
                await asyncio.sleep(2 ** attempt)
        return None, last_error

    async def _health_check_loop(self):
        while self._running:
            await asyncio.sleep(30)
            if not self._browser or not self._browser.is_connected():
                log.warning("browser_disconnected, attempting recovery")
                await self._recover()

    async def _recover(self):
        try:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
            launch_kwargs: Dict[str, Any] = {
                "headless": settings.browser_headless,
                "args": ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
            }
            if settings.proxy_enabled and settings.proxy_url:
                launch_kwargs["proxy"] = {"server": settings.proxy_url}
            self._browser = await self._playwright.chromium.launch(**launch_kwargs)
            for _ in range(self._max_contexts):
                ctx = await self._create_context()
                await self._available_contexts.put(ctx)
            log.info("browser_recovered")
        except Exception as e:
            log.error("browser_recovery_failed", error=e)

    async def stop(self):
        self._running = False
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
        while not self._available_contexts.empty():
            try:
                ctx = self._available_contexts.get_nowait()
                await ctx.close()
            except Exception:
                pass
        for ctx_id in list(self._busy_contexts):
            pass
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        log.info("browser_stopped")

    @property
    def is_running(self) -> bool:
        return self._running and self._browser is not None and self._browser.is_connected()


class CAPTCHADetector:
    PATTERNS = [
        "recaptcha",
        "g-recaptcha",
        "hcaptcha",
        "cf-turnstile",
        "captcha",
        "security check",
        "verify you are human",
        "robot check",
    ]

    SELECTORS = [
        "iframe[src*='recaptcha']",
        "iframe[src*='hcaptcha']",
        "iframe[src*='turnstile']",
        ".g-recaptcha",
        ".h-captcha",
        "div[class*='captcha']",
        "#captcha",
    ]

    @classmethod
    async def check_page(cls, page: Page) -> bool:
        try:
            page_text = await page.inner_text("body")
            page_text_lower = page_text.lower()
            for pattern in cls.PATTERNS:
                if pattern in page_text_lower:
                    record_captcha()
                    return True

            for selector in cls.SELECTORS:
                element = await page.query_selector(selector)
                if element:
                    record_captcha()
                    return True
        except Exception:
            pass
        return False

    @classmethod
    def check_text(cls, text: str) -> bool:
        text_lower = text.lower()
        for pattern in cls.PATTERNS:
            if pattern in text_lower:
                record_captcha()
                return True
        return False


def is_timeout_error(e: Exception) -> bool:
    return isinstance(e, PWTimeout)


def is_connection_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(w in msg for w in ["connection", "refused", "reset", "timeout", "econnrefused"])
