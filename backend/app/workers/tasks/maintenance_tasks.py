from __future__ import annotations

import asyncio
from typing import Any, Dict

from app.celery_app import celery_app


@celery_app.task(name="run_admin_maintenance_task")
def run_admin_maintenance_task(action: str) -> Dict[str, Any]:
    if action == "rebuild_lifecycle":
        from app.services.lifecycle_rebuilder_service import LifecycleRebuilderService

        return LifecycleRebuilderService.rebuild()
    if action == "rebuild_agencies":
        from app.services.agency_master_service import AgencyMasterService

        service = AgencyMasterService()
        try:
            return service.build_and_import()
        finally:
            service.close()
    if action == "import_opening_reports":
        from app.services.opening_report_importer import OpeningReportImporterService

        return OpeningReportImporterService.import_all()
    if action == "rebuild_contractor_dna":
        return asyncio.run(_rebuild_contractor_dna())
    raise ValueError(f"Unsupported maintenance action: {action}")


async def _rebuild_contractor_dna() -> Dict[str, Any]:
    from app.db.database import get_async_session
    from app.services.contractor_dna_service import ContractorDNAService

    async with get_async_session() as session:
        service = ContractorDNAService(session)
        return await service.rebuild_contractor_intelligence()
