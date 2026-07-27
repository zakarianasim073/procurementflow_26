"""
Agent 1 - Tender Radar Agent v2.0
Daily e-GP scanner: live tenders, APP plans, NOA awards, eContracts.
Tracks what's been imported, deduplicates, stores structured data.
"""
from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.agents.egp_client import eGPClient
from app.services.runtime_guards import distributed_lock
import logging

logger = logging.getLogger(__name__)

IMPORT_TRACKER_KEY = "egp_import_tracker"

class TenderRadarAgent(BaseAgent):
    agent_id = "agent-001-tender-radar"
    agent_name = "Tender Radar"
    description = "Daily e-GP scanner: live tenders, APP plans, NOA awards, eContracts"
    dependencies = []
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        action = context.get("action", "match_existing")
        
        if action in {"scan_live_tenders", "scan_all"}:
            async with distributed_lock("agent-001-tender-radar:scan_all", ttl=1800) as acquired:
                if not acquired:
                    return AgentResult(
                        status=AgentStatus.SKIPPED,
                        output={"status": "locked", "message": "Tender radar scan already running"},
                    )
                return await self._scan_all()
        
        # Legacy matching support
        tenders = context.get("tenders", [])
        filters = context.get("filters", {})
        matched = self._match_existing(tenders, filters)
        
        return AgentResult(
            status=AgentStatus.SUCCESS,
            output={"matched_tenders": matched, "total": len(matched), "scanned": len(tenders)}
        )

    async def _scan_all(self) -> AgentResult:
        """Scan e-GP for all new data: live tenders, APP, NOA awards."""
        from app.db.database import get_session
        from app.services.intelligence_data_service_facade import IntelligenceDataServiceFacade as IntelligenceDataService
        
        tracker = await self._load_tracker()
        now = datetime.now(timezone.utc)
        results = {"live_tenders": {"found": 0, "new": 0}, "app": {"found": 0, "new": 0}, "noa": {"found": 0, "new": 0}}
        client = eGPClient(timeout=30)
        try:
            client.client.get("https://www.eprocure.gov.bd")  # seed session
        except Exception as e:
            logger.error("e-GP portal unavailable during radar seed request: %s", e, exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                error=f"e-GP portal unavailable: {e}",
                output={"results": results, "tracker_keys": list(tracker.keys())},
            )

        # ── 1. Scan ALL live tenders via advance search ──
        try:
            logger.info("=== Scanning e-GP LIVE tenders (advance search, all pages) ===")
            all_live = []
            for page in range(1, 6):  # up to 5 pages × 100 = 500 tenders
                tenders = client.search_tender(keyword="", page=page, size=100)
                if not tenders:
                    break
                all_live.extend(tenders)
                if len(tenders) < 100:
                    break
            
            # Filter to Works only (civil construction)
            works_only = [t for t in all_live if t.category and t.category.lower() == "works"]
            skipped = len(all_live) - len(works_only)
            if skipped:
                logger.info(f"Filtered out {skipped} non-Works tenders (Goods/Services)")
            all_live = works_only
            
            results["live_tenders"]["found"] = len(all_live)
            
            # Dedup against DB
            new_tenders = []
            async with get_session() as session:
                svc = IntelligenceDataService(session)
                for t in all_live:
                    exists = await self._tender_exists(session, t.tender_id, t.title or "")
                    if not exists:
                        new_tenders.append(t)
                
                results["live_tenders"]["new"] = len(new_tenders)
                
                # Import each tender individually so one failure doesn't kill all
                imported_ok = 0
                for t in new_tenders:
                    try:
                        async with session.begin_nested():
                            await self._import_live_tender(svc, t)
                        imported_ok += 1
                    except Exception as e:
                        logger.warning(f"Skipping tender {t.tender_id}: {e}")
                
                if imported_ok > 0:
                    await session.commit()
                    logger.info(f"Imported {imported_ok}/{len(new_tenders)} live tenders")
                    logger.info(f"Imported {len(new_tenders)} new live tenders")
                    
                    # Broadcast alert
                    await self.share_knowledge(
                        entry_type="tender_import",
                        tender_id="_batch",
                        data={"count": len(new_tenders), "type": "live", "tenders": [t.tender_id for t in new_tenders]},
                        summary=f"{len(new_tenders)} new live tenders imported from e-GP",
                        tags=["egp_import", "live_tenders"]
                    )
        except Exception as e:
            logger.error(f"Live tender scan failed: {e}", exc_info=True)
            results["live_tenders"]["error"] = str(e)

        # ── 2. Scan APP data ──
        try:
            logger.info("=== Scanning e-GP APP data ===")
            app_results = []
            # Search multiple keywords to cover all agencies
            for kw in ["CPA", "BWDB", "LGED", "PWD", "BBA", "RHD", "Works", "Construction"]:
                items = client.search_app(keyword=kw)
                app_results.extend(items)
            
            # Dedup by app_code
            seen_codes = set()
            unique_apps = []
            for item in app_results:
                code = item.get("app_code", "") or item.get("package_no", "")
                if code not in seen_codes:
                    seen_codes.add(code)
                    unique_apps.append(item)
            
            results["app"]["found"] = len(unique_apps)
            
            async with get_session() as session:
                svc = IntelligenceDataService(session)
                new_apps = []
                for item in unique_apps:
                    exists = await self._app_exists(session, item)
                    if not exists:
                        new_apps.append(item)
                
                results["app"]["new"] = len(new_apps)
                
                imported_apps = 0
                for item in new_apps:
                    try:
                        async with session.begin_nested():
                            await self._import_app_record(svc, item)
                        imported_apps += 1
                    except Exception as e:
                        logger.warning(f"Skipping APP item: {e}")
                
                if imported_apps > 0:
                    await session.commit()
                    logger.info(f"Imported {imported_apps}/{len(new_apps)} new APP records")
        except Exception as e:
            logger.error(f"APP scan failed: {e}", exc_info=True)
            results["app"]["error"] = str(e)

        # ── 3. Scan NOA awards ──
        try:
            logger.info("=== Scanning e-GP NOA awards ===")
            noa_results = []
            for kw in ["Works", "Construction", "CPA", "BWDB", "LGED", "PWD"]:
                awards = client.search_noa(entity=kw, days=30)
                noa_results.extend(awards)
            
            results["noa"]["found"] = len(noa_results)
            
            async with get_session() as session:
                svc = IntelligenceDataService(session)
                new_noa = []
                for item in noa_results:
                    exists = await self._noa_exists(session, item)
                    if not exists:
                        new_noa.append(item)
                
                results["noa"]["new"] = len(new_noa)

                imported_noa = 0
                for item in new_noa:
                    try:
                        async with session.begin_nested():
                            await self._import_noa_award(svc, item)
                        imported_noa += 1
                    except Exception as e:
                        logger.warning(f"Skipping NOA item: {e}")

                if imported_noa > 0:
                    await session.commit()
                    logger.info(f"Imported {imported_noa}/{len(new_noa)} new NOA awards")

                    await self.share_knowledge(
                        entry_type="noa_alert",
                        tender_id="_batch",
                        data={"count": len(new_noa), "awards": new_noa[:50]},
                        summary=f"{len(new_noa)} new NOA awards found from e-GP",
                        tags=["egp_import", "noa"]
                    )
        except Exception as e:
            logger.error(f"NOA scan failed: {e}", exc_info=True)
            results["noa"]["error"] = str(e)

        # ── Update tracker ──
        tracker["last_scan_at"] = now.isoformat()
        tracker["last_results"] = results
        await self._save_tracker(tracker)
        
        # Broadcast summary
        summary = (
            f"Live tenders: {results['live_tenders']['new']}/{results['live_tenders']['found']} new | "
            f"APP: {results['app']['new']}/{results['app']['found']} new | "
            f"NOA: {results['noa']['new']}/{results['noa']['found']} new"
        )
        await self.share_knowledge(
            entry_type="radar_scan_summary",
            tender_id="_daily",
            data={"results": results, "tracker": tracker},
            summary=summary,
            tags=["egp_import", "daily_scan"]
        )
        
        client.close()
        
        return AgentResult(
            status=AgentStatus.SUCCESS,
            output={"results": results, "tracker_keys": list(tracker.keys())}
        )

    # ── DB helpers ──

    async def _tender_exists(self, session, tender_id: str, title: str) -> bool:
        """Check if tender already in procurement_tenders or tender_data_pool."""
        from sqlalchemy import select, text
        
        result = await session.execute(
            text("SELECT 1 FROM live_tender_sources WHERE source_tender_id = :tid LIMIT 1"),
            {"tid": tender_id}
        )
        if result.scalar():
            return True
        
        result = await session.execute(
            text("SELECT 1 FROM procurement_tenders WHERE package_no LIKE :pid LIMIT 1"),
            {"pid": f"%{tender_id}%"}
        )
        return bool(result.scalar())

    async def _app_exists(self, session, item: Dict) -> bool:
        """Check if APP record already imported."""
        from sqlalchemy import text
        app_code = item.get("app_code", "") or item.get("package_no", "")
        if app_code:
            result = await session.execute(
                text("SELECT 1 FROM app_records WHERE app_code = :code LIMIT 1"),
                {"code": app_code}
            )
            if result.scalar():
                return True
        tender_id = item.get("tender_id", "")
        if tender_id:
            result = await session.execute(
                text("SELECT 1 FROM app_records WHERE source_tender_id = :tid LIMIT 1"),
                {"tid": tender_id}
            )
            if result.scalar():
                return True
        return False

    async def _noa_exists(self, session, item: Dict) -> bool:
        """Check if NOA already imported."""
        from sqlalchemy import text
        tender_id = item.get("tender_id", "")
        if tender_id:
            result = await session.execute(
                text("SELECT 1 FROM award_records_v2 WHERE source_tender_id = :tid LIMIT 1"),
                {"tid": tender_id}
            )
            if result.scalar():
                return True
        return False

    async def _import_live_tender(self, svc, tender):
        """Import a live tender into the canonical intelligence tables."""
        await svc.ingest_live_tender_notice(tender, source_type="egp_live_scan")

    async def _import_app_record(self, svc, item: Dict):
        """Import an APP record into the canonical intelligence tables."""
        await svc.ingest_app_plan_record(item, source_type="egp_app_scan")

    async def _import_noa_award(self, svc, item: Dict):
        """Import a NOA award into the canonical intelligence tables."""
        await svc.ingest_noa_award_notice(item, source_type="egp_noa_scan")

    async def _load_tracker(self) -> Dict:
        """Load import tracker from brain knowledge."""
        entries = await self.query_brain(entry_type=IMPORT_TRACKER_KEY, tender_id="_global")
        if entries:
            return entries[0].get("data", {})
        return {"last_scan_at": None, "total_imported_live": 0, "total_imported_app": 0, "total_imported_noa": 0}

    async def _save_tracker(self, tracker: Dict):
        """Save import tracker to brain knowledge."""
        await self.share_knowledge(
            entry_type=IMPORT_TRACKER_KEY,
            tender_id="_global",
            data=tracker,
            summary=f"Last scan: {tracker.get('last_scan_at', 'never')}",
            tags=["egp_import", "tracker"]
        )

    # ── Legacy matching ──

    def _match_existing(self, tenders: List, filters: Dict) -> List:
        """Legacy scoring for provided tender list."""
        matched = []
        for t in tenders:
            score = self._match_score(t, filters)
            if score > 0:
                matched.append({"tender_id": t.get("tender_id"), "title": t.get("title"), "score": score})
        return matched

    def _match_score(self, tender: Dict, filters: Dict) -> float:
        score = 50.0
        if filters.get("agency") and filters["agency"].lower() in str(tender.get("agency", "")).lower():
            score += 20
        if filters.get("min_value") and float(tender.get("estimated_amount_bdt", 0)) >= filters["min_value"]:
            score += 15
        if filters.get("max_value") and float(tender.get("estimated_amount_bdt", 0)) <= filters["max_value"]:
            score += 15
        return score

    @staticmethod
    def _parse_date(dt_str: Optional[str]):
        """Try to parse e-GP date string to datetime."""
        if not dt_str:
            return None
        for fmt in ["%d-%b-%Y %H:%M", "%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"]:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        return None
