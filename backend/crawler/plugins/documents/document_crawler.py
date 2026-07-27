from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...database.repository import CrawlRepository
from ...framework.config import settings
from ...framework.logger import get_logger
from ...framework.storage import save_raw_record
from ..base import BaseCrawler
from ..registry import register

log = get_logger("crawler.documents")

SUBDL_SCRIPT = Path(__file__).resolve().parent / ".." / ".." / "utils" / "_sub_dl_crawler.py"

SECTION_KEYWORDS = {
    "NIT": ["notice", "nit"],
    "TDS": ["section2", "tender data sheet", "tds"],
    "BOQ": ["section6", "bill of quantities", "boq", "bill of quantit"],
    "GCC": ["section3", "general conditions", "gcc"],
    "PCC": ["section4", "particular conditions", "pcc"],
    "FORMS": ["section5", "tender and contract forms"],
    "SPEC_GEN": ["section7", "general specifications"],
    "SPEC_PART": ["section8", "particular specifications"],
    "SPEC_ES": ["section9", "es specifications"],
    "DRAWINGS": ["section10", "drawings"],
    "APPENDIX": ["section11", "appendix"],
    "CORRIGENDUM": ["corrigendum", "addendum"],
}


def _classify_document(filepath: str) -> str:
    name = Path(filepath).name.lower()
    parent = Path(filepath).parent.name.lower()
    combined = f"{parent} {name}"
    for doc_type, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return doc_type
    return "OTHER"


@register("documents")
class DocumentCrawler(BaseCrawler):
    name = "documents"

    async def execute(self):
        """Override default lifecycle: download docs for each tender from parse_list."""
        self.ctx._crawl_log.start()
        self._running = True
        try:
            await self.setup()
            await self.search()
            items = await self.parse_list()
            for item in items:
                if not self._running:
                    break
                tender_id = item.get("tender_id", item.get("id", ""))
                if not tender_id:
                    continue
                result = await self._download_for_tender(tender_id)
                await self._store_document_metadata(tender_id, result)
                await self._extract_and_feed_brain(tender_id, result)
                await asyncio.sleep(settings.rate_limit_min_s)
            await self.finish()
            self.ctx._crawl_log.finish("success")
        except Exception as e:
            self.ctx.log.error("crawl_execution_failed", error=str(e))
            self.ctx._crawl_log.finish("failed", str(e))
        finally:
            self._running = False
        return self.ctx._crawl_log

    async def initialize(self):
        pass

    async def search(self):
        self._tender_ids = self.ctx.config.get("tender_ids", [])
        self._from_brain = self.ctx.config.get("from_brain", False)

    async def parse_list(self) -> List[Dict[str, Any]]:
        if self._tender_ids:
            return [{"tender_id": tid} for tid in self._tender_ids]
        if self._from_brain:
            return await self._fetch_pending_from_brain()
        return []

    async def next_page(self) -> bool:
        return False

    async def _fetch_pending_from_brain(self) -> List[Dict[str, Any]]:
        try:
            from ...framework.storage import get_storage_manager
            sm = get_storage_manager()
            records = sm.load_raw_records("raw_tenders", limit=50)
            existing = await self._get_downloaded_ids()
            return [
                {"tender_id": r.get("tender_id")}
                for r in records
                if r.get("tender_id") and r["tender_id"] not in existing
            ]
        except Exception as e:
            self.ctx.log.error("fetch_pending_failed", error=str(e))
            return []

    async def _get_downloaded_ids(self) -> set:
        try:
            pool = await self._get_pool()
            if pool:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("SELECT DISTINCT tender_id FROM crawl_documents")
                    return {r["tender_id"] for r in rows}
        except Exception:
            pass
        return set()

    async def _get_pool(self):
        from ...database.connection import get_db_pool
        try:
            return await get_db_pool()
        except Exception:
            return None

    async def _download_for_tender(self, tender_id: str) -> Dict[str, Any]:
        """Download tender documents via subprocess (bypasses WinError 10060)."""
        result = {"tender_id": tender_id, "files": [], "status": "pending"}
        uploads_dir = settings.output_dir.parent.parent / "uploads" / tender_id
        uploads_dir.mkdir(parents=True, exist_ok=True)

        if not SUBDL_SCRIPT.exists():
            self.ctx.log.error("subdl_script_not_found", path=str(SUBDL_SCRIPT))
            result["status"] = "subprocess_unavailable"
            return result

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(SUBDL_SCRIPT), tender_id, str(uploads_dir),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=str(SUBDL_SCRIPT.parent),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            if stdout:
                output = stdout.decode().strip()
                if output:
                    try:
                        files = json.loads(output)
                        if isinstance(files, list):
                            result["files"] = files
                    except json.JSONDecodeError:
                        self.ctx.log.warning("subprocess_json_parse_failed", output=output[:200])
            if stderr:
                err = stderr.decode().strip()
                if err:
                    self.ctx.log.warning("subprocess_stderr", error=err[:500])
            result["status"] = "success"
        except asyncio.TimeoutError:
            result["status"] = "timeout"
            self.ctx.log.error("subprocess_timeout", tender_id=tender_id)
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self.ctx.log.error("subprocess_error", tender_id=tender_id, error=str(e))

        return result

    async def _store_document_metadata(self, tender_id: str, result: Dict[str, Any]):
        """Store document metadata in crawl_documents table (framework) + pf_documents (normalized)."""
        saved = 0
        for f in result.get("files", []):
            doc_type = f.get("doc_type", "OTHER")
            if doc_type == "extracted":
                doc_type = _classify_document(f.get("path", ""))
            elif doc_type == "ZIP":
                continue

            path = f.get("path", "")
            if not path or not Path(path).exists():
                continue

            try:
                await CrawlRepository.save_document(
                    tender_id=tender_id,
                    doc_type=doc_type,
                    filename=f.get("filename", Path(path).name),
                    file_path=path,
                    file_size=f.get("size_bytes", 0),
                    source_url=f.get("url", ""),
                    file_hash=f.get("hash", ""),
                    metadata={
                        "source": f.get("source", ""),
                        "tender_id": tender_id,
                        "doc_type_raw": f.get("doc_type", ""),
                    },
                )
                # Phase 3: normalize into pf_documents
                try:
                    from ...database.normalizer import get_normalizer
                    norm = get_normalizer()
                    await norm.upsert_document({
                        "tender_id": tender_id,
                        "doc_type": doc_type,
                        "filename": f.get("filename", Path(path).name),
                        "file_path": path,
                        "file_size": f.get("size_bytes", 0),
                        "file_hash": f.get("hash", ""),
                        "source_url": f.get("url", ""),
                        "metadata": {"source": f.get("source", ""), "doc_type_raw": f.get("doc_type", "")},
                    })
                except Exception as ne:
                    self.ctx.log.warning("document_normalize_failed", error=str(ne))
                saved += 1
            except Exception as e:
                self.ctx.log.error("document_save_failed", path=path, error=str(e))

        if saved == 0:
            save_raw_record("raw_documents", "eprocure_documents", {
                "tender_id": tender_id, "files": result.get("files", [])
            })
        self.ctx.items_saved = saved
        self.ctx._crawl_log.progress(items_done=saved)

    async def _extract_and_feed_brain(self, tender_id: str, result: Dict[str, Any]):
        """Extract BOQ/TDS text from PDFs and feed to brain knowledge_entries.
        
        Falls back to direct DB insert for knowledge_entries if brain not available.
        """
        files = result.get("files", [])
        boq_path = self._find_doc(files, "BOQ")
        tds_path = self._find_doc(files, "TDS")
        nit_path = self._find_doc(files, "NIT")
        if not nit_path:
            nit_path = next(
                (f.get("path") for f in files if f.get("filename") == "notice.pdf"),
                None,
            )

        try:
            import pdfplumber
        except ImportError:
            self.ctx.log.warning("pdfplumber_not_available")
            return

        entries = []

        # Tender document manifest
        manifest = {
            "tender_id": tender_id,
            "file_count": len(files),
            "files": [
                {"type": f.get("doc_type"), "filename": f.get("filename"),
                 "path": f.get("path"), "size_bytes": f.get("size_bytes")}
                for f in files
            ],
        }
        entries.append(("tender_document", manifest, manifest))

        # BOQ text
        if boq_path and Path(boq_path).exists():
            try:
                with pdfplumber.open(boq_path) as pdf:
                    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                if text.strip():
                    entries.append(("boq_text", {"tender_id": tender_id, "text": text[:50000], "source_file": boq_path}, {"tender_id": tender_id}))
            except Exception as e:
                self.ctx.log.warning("boq_extraction_failed", error=str(e))

        # TDS text
        if tds_path and Path(tds_path).exists():
            try:
                with pdfplumber.open(tds_path) as pdf:
                    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                if text.strip():
                    entries.append(("tds_text", {"tender_id": tender_id, "text": text[:50000], "source_file": tds_path}, {"tender_id": tender_id}))
            except Exception as e:
                self.ctx.log.warning("tds_extraction_failed", error=str(e))

        # NIT text
        if nit_path and Path(nit_path).exists():
            try:
                with pdfplumber.open(nit_path) as pdf:
                    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                if text.strip():
                    entries.append(("nit_text", {"tender_id": tender_id, "text": text[:30000], "source_file": nit_path}, {"tender_id": tender_id}))
            except Exception:
                pass

        for entry_type, data, tags_src in entries:
            try:
                await self._insert_knowledge(tender_id, entry_type, data)
            except Exception as e:
                self.ctx.log.warning("knowledge_insert_failed", type=entry_type, error=str(e))

    def _find_doc(self, files: list, doc_type: str) -> Optional[str]:
        for f in files:
            if f.get("doc_type") == doc_type:
                return f.get("path")
            name = Path(f.get("path", "")).name.lower()
            parent = Path(f.get("path", "")).parent.name.lower()
            combined = f"{parent} {name}"
            for kw in SECTION_KEYWORDS.get(doc_type, []):
                if kw in combined:
                    return f.get("path")
        return None

    async def _insert_knowledge(self, tender_id: str, entry_type: str, data: dict):
        """Insert directly into knowledge_entries via raw SQL."""
        import uuid
        pool = await self._get_pool()
        if not pool:
            return
        checksum = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO knowledge_entries (id, entry_type, tender_id, data, checksum, source, created_at, updated_at)
                   VALUES ($1, $2, $3, $4::jsonb, $5, $6, NOW(), NOW())
                   ON CONFLICT (id) DO NOTHING""",
                str(uuid.uuid4()), entry_type, tender_id,
                json.dumps(data, default=str), checksum, "crawler.documents",
            )
