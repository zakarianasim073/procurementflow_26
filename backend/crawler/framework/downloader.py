from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import httpx

from .config import settings
from .logger import get_logger
from .metrics import get_metrics, track_duration
from .url_policy import validate_crawler_url

log = get_logger("crawler.downloader")

DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

DOWNLOAD_EXTENSIONS: Set[str] = set(DOCUMENT_TYPES.keys())


class DocumentDownloader:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.download_temp_path
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._client: Optional[httpx.AsyncClient] = None
        self._sem: asyncio.Semaphore = asyncio.Semaphore(3)
        self._downloaded: Set[str] = set()

    async def start(self):
        self._client = httpx.AsyncClient(
            verify=True,
            follow_redirects=True,
            timeout=httpx.Timeout(120.0, connect=30.0, read=60.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        log.info("downloader_started")

    async def stop(self):
        if self._client:
            await self._client.aclose()
        log.info("downloader_stopped")

    async def download(
        self,
        url: str,
        sub_dir: str = "",
        filename: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        referer: Optional[str] = None,
    ) -> Optional[Path]:
        if not self._client:
            raise RuntimeError("Downloader not started")
        validate_crawler_url(url)

        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        if url_hash in self._downloaded:
            return None
        self._downloaded.add(url_hash)

        async with self._sem:
            with track_duration(get_metrics().items_downloaded):
                try:
                    request_headers = headers or {}
                    if referer:
                        request_headers["Referer"] = referer

                    resp = await self._client.get(url, headers=request_headers)
                    resp.raise_for_status()

                    content = resp.content
                    content_type = resp.headers.get("content-type", "")

                    if not content or len(content) < 100:
                        log.warning("download_too_small", url=url, size=len(content))
                        return None

                    if filename:
                        save_name = filename
                    else:
                        parsed = urlparse(url)
                        base_name = os.path.basename(parsed.path)
                        if not base_name or "." not in base_name:
                            ext = self._detect_extension(content_type, url)
                            base_name = f"{url_hash}{ext}"
                        save_name = base_name

                    safe_sub_dir = Path(sub_dir)
                    if safe_sub_dir.is_absolute() or ".." in safe_sub_dir.parts:
                        raise ValueError("unsafe download sub-directory")
                    save_name = Path(save_name).name
                    save_dir = self.base_dir / safe_sub_dir
                    save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = save_dir / save_name

                    if save_path.exists() and save_path.stat().st_size == len(content):
                        return save_path

                    save_path.write_bytes(content)
                    log.info("download_complete", url=url, path=str(save_path), size=len(content))
                    return save_path

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        log.warning("download_404", url=url)
                    else:
                        log.warning("download_http_error", url=url, status=e.response.status_code)
                    return None
                except Exception as e:
                    log.error("download_failed", url=url, error=e)
                    return None

    async def download_zip(
        self,
        url: str,
        sub_dir: str = "",
        filename: str = "documents.zip",
        referer: Optional[str] = None,
    ) -> Optional[Path]:
        result = await self.download(url, sub_dir=sub_dir, filename=filename, referer=referer)
        if result and result.suffix == ".zip":
            import zipfile
            try:
                extract_dir = result.parent / result.stem
                extract_dir.mkdir(exist_ok=True)
                with zipfile.ZipFile(result, "r") as zf:
                    for member in zf.infolist():
                        target = (extract_dir / member.filename).resolve()
                        if extract_dir.resolve() not in target.parents and target != extract_dir.resolve():
                            raise ValueError("unsafe ZIP member path")
                    zf.extractall(extract_dir)
                log.info("zip_extracted", path=str(result), extract_dir=str(extract_dir))
            except zipfile.BadZipFile:
                log.warning("bad_zip", path=str(result))
        return result

    async def download_pdf(
        self,
        url: str,
        sub_dir: str = "",
        filename: Optional[str] = None,
    ) -> Optional[Path]:
        return await self.download(url, sub_dir=sub_dir, filename=filename)

    def _detect_extension(self, content_type: str, url: str) -> str:
        for ext, ctype in DOCUMENT_TYPES.items():
            if ctype in content_type:
                return ext
        parsed = urlparse(url)
        _, ext = os.path.splitext(parsed.path)
        if ext:
            return ext
        return ".bin"

    @staticmethod
    def is_downloadable_url(url: str) -> bool:
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1].lower()
        return ext in DOWNLOAD_EXTENSIONS or any(
            kw in url.lower() for kw in ["download", "attachment", "getfile", "servlet"]
        )


_downloader: Optional[DocumentDownloader] = None


def get_downloader() -> DocumentDownloader:
    global _downloader
    if _downloader is None:
        _downloader = DocumentDownloader()
    return _downloader
