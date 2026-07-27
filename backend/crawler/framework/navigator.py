from __future__ import annotations

import asyncio
from typing import Callable, Optional

from playwright.async_api import Page, Response, TimeoutError as PWTimeout

from .config import settings
from .logger import get_logger
from .browser import CAPTCHADetector
from .metrics import track_duration, get_metrics

log = get_logger("crawler.navigator")


class Navigator:
    def __init__(self, page: Page):
        self.page = page
        self._current_url: Optional[str] = None

    async def goto(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: Optional[int] = None,
        referer: Optional[str] = None,
        check_captcha: bool = True,
    ) -> Optional[Response]:
        # e-GP pages rarely reach network-idle (persistent connections / analytics),
        # which makes networkidle waits block for the full timeout on every request.
        # Always use domcontentloaded for fast, reliable scraping.
        if wait_until == "networkidle":
            wait_until = "domcontentloaded"
        timeout = timeout or settings.browser_navigation_timeout_ms
        with track_duration(get_metrics().pages_crawled):
            try:
                resp = await self.page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=timeout,
                    referer=referer,
                )
                self._current_url = self.page.url

                if check_captcha and settings.captcha_detect_enabled:
                    if await CAPTCHADetector.check_page(self.page):
                        log.warning("captcha_detected", url=url)
                        return None

                return resp
            except PWTimeout as e:
                log.warning("nav_timeout", url=url, timeout=timeout)
                raise
            except Exception as e:
                log.error("nav_failed", url=url, error=e)
                raise

    async def wait_ready(self, timeout: Optional[int] = None):
        """Fast, non-blocking wait for the page to be interactive.

        Uses domcontentloaded (never networkidle) and degrades gracefully on
        timeout so a single slow page never stalls the whole crawl.
        """
        timeout = timeout or min(settings.browser_timeout_ms, 15000)
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except Exception:
            pass

    async def click_and_wait(
        self,
        selector: str,
        wait_until: str = "domcontentloaded",
        timeout: Optional[int] = None,
    ) -> bool:
        timeout = timeout or settings.browser_navigation_timeout_ms
        try:
            async with self.page.expect_navigation(timeout=timeout):
                await self.page.click(selector)
            await self.page.wait_for_load_state(wait_until, timeout=timeout)
            return True
        except Exception as e:
            log.warning("click_nav_failed", selector=selector, error=e)
            return False

    async def fill_and_submit(
        self,
        form_selectors: dict,
        submit_selector: str,
        wait_until: str = "networkidle",
    ) -> bool:
        for field_selector, value in form_selectors.items():
            await self.page.fill(field_selector, str(value))
        return await self.click_and_wait(submit_selector, wait_until=wait_until)

    async def wait_for_selector(
        self,
        selector: str,
        state: str = "visible",
        timeout: Optional[int] = None,
    ) -> bool:
        timeout = timeout or settings.browser_timeout_ms
        try:
            await self.page.wait_for_selector(selector, state=state, timeout=timeout)
            return True
        except PWTimeout:
            return False

    async def wait_for_text(self, text: str, timeout: Optional[int] = None) -> bool:
        timeout = timeout or settings.browser_timeout_ms
        try:
            await self.page.wait_for_function(
                f'document.body.innerText.includes("{text}")',
                timeout=timeout,
            )
            return True
        except PWTimeout:
            return False

    async def detect_navigation_complete(self) -> bool:
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            return True
        except Exception:
            return False

    @property
    def current_url(self) -> Optional[str]:
        try:
            return self.page.url
        except Exception:
            return self._current_url
