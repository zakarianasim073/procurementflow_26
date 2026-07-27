from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

from .config import settings
from .logger import get_logger
from .metrics import record_error, record_captcha

log = get_logger("crawler.captcha")


class CAPTCHASolver:
    def __init__(self):
        self._api_key: Optional[str] = None
        self._service_url: str = "https://2captcha.com"
        self._running: bool = False

    async def start(self):
        self._running = True
        self._api_key = settings.captcha_solver_service or os.getenv("TWOCAPTCHA_API_KEY")
        if self._api_key:
            log.info("captcha_solver_started", service="2captcha")
        else:
            log.warning("captcha_solver_no_api_key")

    async def stop(self):
        self._running = False
        log.info("captcha_solver_stopped")

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        timeout_s: int = 120,
    ) -> Optional[str]:
        if not self._api_key:
            record_error("captcha_no_api_key")
            return None
        record_captcha()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
                resp = await client.post(
                    f"{self._service_url}/in.php",
                    data={
                        "key": self._api_key,
                        "method": "userrecaptcha",
                        "googlekey": site_key,
                        "pageurl": page_url,
                        "json": 1,
                    },
                )
                result = resp.json()
                if result.get("status") != 1:
                    log.error("captcha_submit_failed", error=result.get("request"))
                    return None
                captcha_id = result["request"]
                for _ in range(timeout_s // 5):
                    await asyncio.sleep(5)
                    resp = await client.post(
                        f"{self._service_url}/res.php",
                        data={
                            "key": self._api_key,
                            "action": "get",
                            "id": captcha_id,
                            "json": 1,
                        },
                    )
                    result = resp.json()
                    if result.get("status") == 1:
                        return result["request"]
                    if result.get("request") != "CAPCHA_NOT_READY":
                        log.error("captcha_error", error=result.get("request"))
                        return None
                log.error("captcha_timeout")
                return None
        except Exception as e:
            log.error("captcha_solver_exception", error=str(e))
            return None

    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.3,
        timeout_s: int = 60,
    ) -> Optional[str]:
        if not self._api_key:
            return None
        record_captcha()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
                resp = await client.post(
                    f"{self._service_url}/in.php",
                    data={
                        "key": self._api_key,
                        "method": "recaptchav3",
                        "googlekey": site_key,
                        "pageurl": page_url,
                        "action": action,
                        "min_score": min_score,
                        "json": 1,
                    },
                )
                result = resp.json()
                if result.get("status") != 1:
                    return None
                captcha_id = result["request"]
                for _ in range(timeout_s // 5):
                    await asyncio.sleep(5)
                    resp = await client.post(
                        f"{self._service_url}/res.php",
                        data={
                            "key": self._api_key,
                            "action": "get",
                            "id": captcha_id,
                            "json": 1,
                        },
                    )
                    result = resp.json()
                    if result.get("status") == 1:
                        return result["request"]
                    if result.get("request") != "CAPCHA_NOT_READY":
                        return None
                return None
        except Exception as e:
            log.error("captcha_v3_exception", error=str(e))
            return None

    async def solve_image_captcha(
        self,
        image_base64: str,
        timeout_s: int = 60,
    ) -> Optional[str]:
        if not self._api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
                resp = await client.post(
                    f"{self._service_url}/in.php",
                    data={
                        "key": self._api_key,
                        "method": "base64",
                        "body": image_base64,
                        "json": 1,
                    },
                )
                result = resp.json()
                if result.get("status") != 1:
                    return None
                captcha_id = result["request"]
                for _ in range(timeout_s // 5):
                    await asyncio.sleep(5)
                    resp = await client.post(
                        f"{self._service_url}/res.php",
                        data={
                            "key": self._api_key,
                            "action": "get",
                            "id": captcha_id,
                            "json": 1,
                        },
                    )
                    result = resp.json()
                    if result.get("status") == 1:
                        return result["request"]
                    if result.get("request") != "CAPCHA_NOT_READY":
                        return None
                return None
        except Exception as e:
            log.error("image_captcha_exception", error=str(e))
            return None

    def is_available(self) -> bool:
        return self._api_key is not None


_captcha_solver: Optional[CAPTCHASolver] = None


def get_captcha_solver() -> CAPTCHASolver:
    global _captcha_solver
    if _captcha_solver is None:
        _captcha_solver = CAPTCHASolver()
    return _captcha_solver


async def init_captcha_solver():
    mgr = get_captcha_solver()
    await mgr.start()
    return mgr


async def shutdown_captcha_solver():
    mgr = get_captcha_solver()
    await mgr.stop()
