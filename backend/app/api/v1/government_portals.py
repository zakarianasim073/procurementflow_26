"""
Government Portal Integration API Endpoints

This module defines all API endpoints required to integrate the four Bangladesh government portals:
1. BPPA (citizen.bppa.gov.bd/ocds/view) - OCDS compliance
2. BWDB - Project data API
3. PWD - Project data API  
4. LGED - Project data API

Usage:
    GET /api/government-portal/bppa/tenders
    GET /api/government-portal/bwdb/projects
    GET /api/government-portal/pwd/projects
    GET /api/government-portal/lged/projects
    GET /api/government-portal/cross-reference?package_no=BWDB-CTG-01
    GET /api/government-portal/lifecycle?project_id=BWDB-2024-001

All endpoints return standardized OCDS-compatible data structures.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger("procureflow.government_portals")

from app.core.security import get_optional_user
from app.core.config import settings
from app.db.base import get_async_session
from app.schemas.response_models import (
    GovernmentPortalResponse,
    PortalHealthResponse,
    PortalOrganizationsResponse,
    PortalZonesResponse,
    SuccessWithData,
)

router = APIRouter(prefix="/government-portal", tags=["government-portal"])

# Data Models
class OCDSRelease(BaseModel):
    ocid: str
    id: str
    date: str
    release_type: str
    parties: List[Dict[str, Any]]
    tender: Dict[str, Any]
    contracts: Optional[List[Dict[str, Any]]] = None
    amendments: Optional[List[Dict[str, Any]]] = None
    period: Optional[Dict[str, Any]] = None

class PortalFilters(BaseModel):
    search: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    zone: Optional[str] = None
    agency: Optional[str] = None
    status: Optional[str] = None

# Fallback mock data — used when DB tables don't exist or are empty
GOVERNMENT_DATA = {
    "bppa_ocds": {
        "last_updated": "2026-06-30T00:00:00Z",
        "releases": [
            {
                "ocid": "ocds-1290886-2024",
                "id": "tender-1290886-1",
                "date": "2024-01-15T10:00:00Z",
                "release_type": "tender",
                "parties": [
                    {
                        "id": "party-1",
                        "name": "BWDB Dhaka Division",
                        "type": "procuringEntity",
                        "identifier": {"scheme": "BD-TIN", "id": "1020304050"}
                    }
                ],
                "tender": {
                    "title": "Construction of Storm Water Drainage System",
                    "description": "Civil works including excavation, pipe laying, and surface preparation",
                    "status": "active",
                    "procurementMethod": "open",
                    "value": {"amount": 45500000.00, "currency": "BDT"},
                    "submissionDeadline": "2024-02-15T17:00:00Z",
                    "awardDate": None,
                    "contractPeriod": {"startDate": "2024-03-01", "endDate": "2025-02-28"},
                    "milestones": [
                        {"id": "milestone-1", "title": "Tender Publication", "dueDate": "2024-01-15"},
                        {"id": "milestone-2", "title": "Bid Opening", "dueDate": "2024-02-05"},
                        {"id": "milestone-3", "title": "Contract Award", "dueDate": "2024-02-20"},
                        {"id": "milestone-4", "title": "Project Start", "dueDate": "2024-03-01"}
                    ],
                    "documents": [
                        {"id": "doc-1", "title": " NIT", "description": "Notice Inviting Tender", "format": "pdf", "url": "/docs/nit.pdf"}
                    ],
                    "amendments": []
                },
                "contracts": [
                    {
                        "id": "contract-1",
                        "title": "Storm Water Drainage - Contract 2024",
                        "status": "active",
                        "value": {"amount": 45000000.00, "currency": "BDT"},
                        "period": {"startDate": "2024-03-01", "endDate": "2025-02-28"},
                        "implementation": {
                            "startDate": "2024-03-15",
                            "completionDate": "2025-02-28",
                            "milestones": [
                                {"title": "Phase 1: Excavation", "value": {"amount": 15000000.00}},
                                {"title": "Phase 2: Pipe Installation", "value": {"amount": 18000000.00}},
                                {"title": "Phase 3: Backfilling", "value": {"amount": 12000000.00}}
                            ]
                        },
                        "documents": [
                            {"id": "contract-doc-1", "title": "Contract Agreement", "format": "pdf"}
                        ]
                    }
                ],
                "implementation": {
                    "budgets": [
                        {
                            "category": "civil_works",
                            "amount": 45000000.00,
                            "unit": "BDT",
                            "description": "Total project budget"
                        }
                    ],
                    "milestones": [
                        {"title": "Site Preparation", "startDate": "2024-03-15", "endDate": "2024-04-30", "budget": 5000000.00},
                        {"title": "Installation", "startDate": "2024-05-01", "endDate": "2024-09-30", "budget": 25000000.00},
                        {"title": "Testing", "startDate": "2024-10-01", "endDate": "2024-12-15", "budget": 15000000.00}
                    ],
                    "payments": [
                        {"phase": "milestone_1", "amount": 5000000.00, "date": "2024-05-15", "payee": "contractor-1"},
                        {"phase": "milestone_2", "amount": 15000000.00, "date": "2024-11-15", "payee": "contractor-1"},
                        {"phase": "milestone_3", "amount": 25000000.00, "date": "2025-02-15", "payee": "contractor-1"}
                    ]
                }
            }
        ]
    },
    "bwdb_projects": {
        "last_updated": "2026-06-30T00:00:00Z",
        "projects": [
            {
                "project_id": "BWDB-2024-001",
                "package_no": "BWDB-CTG-01/2024-25",
                "title": "Storm Water Drainage System - Chattogram",
                "description": "Comprehensive stormwater drainage network for Chattogram city",
                "status": "ongoing",
                "created_date": "2024-01-10",
                "updated_date": "2026-06-30",
                "estimated_cost": 45500000.00,
                "actual_cost": 42300000.00,
                "district": "Chattogram",
                "upazila": "Sadar", "station": "CTG-01",
                "division": "Chattogram",
                "sor_agency": "BWDB",
                "zone": "B",
                "sor_rates": {
                    "zone_a": 1250.00,
                    "zone_b": 1320.50,
                    "zone_c": 1450.00,
                    "zone_d": 1380.75
                },
                "documents": [
                    {"id": "doc-1", "title": "Project Report", "type": "project_report", "format": "pdf", "url": "/projects/BWDB-001/report.pdf"},
                    {"id": "doc-2", "title": "BOQ", "type": "boq", "format": "xlsx", "url": "/projects/BWDB-001/boq.xlsx"},
                    {"id": "doc-3", "title": "TDS", "type": "tds", "format": "pdf", "url": "/projects/BWDB-001/tds.pdf"}
                ],
                "milestones": [
                    {"id": "ms-1", "name": "Planning", "status": "completed", "completion_date": "2024-02-01"},
                    {"id": "ms-2", "name": "Design", "status": "completed", "completion_date": "2024-04-15"},
                    {"id": "ms-3", "name": "Implementation", "status": "in_progress", "start_date": "2024-05-01"},
                    {"id": "ms-4", "name": "Monitoring", "status": "pending", "start_date": "2024-10-01"}
                ]
            }
        ]
    },
    "pwd_projects": {
        "last_updated": "2026-06-30T00:00:00Z",
        "projects": [
            {
                "project_id": "PWD-2024-002",
                "package_no": "PWD-CTG-02/2024-25",
                "title": "Road Improvement - Chattogram Port Area",
                "description": "Road widening and improvement at Chattogram Port area",
                "status": "ongoing",
                "created_date": "2024-01-20",
                "updated_date": "2026-06-30",
                "estimated_cost": 28750000.00,
                "actual_cost": 26800000.00,
                "district": "Chattogram",
                "upazila": "Sadar", "station": "CTG-02",
                "division": "Chattogram",
                "sor_agency": "PWD",
                "zone": "B",
                "sor_rates": {
                    "zone_a": 1180.00,
                    "zone_b": 1245.00,
                    "zone_c": 1380.00,
                    "zone_d": 1320.00
                },
                "documents": [
                    {"id": "doc-1", "title": "Project Proposal", "type": "proposal", "format": "pdf", "url": "/projects/PWD-002/proposal.pdf"}
                ]
            }
        ]
    },
    "lged_projects": {
        "last_updated": "2026-06-30T00:00:00Z",
        "projects": [
            {
                "project_id": "LGED-2024-003",
                "package_no": "LGED-CTG-03/2024-25",
                "title": "Water Supply Network Expansion",
                "description": "Expansion of water supply network to unserved areas",
                "status": "ongoing",
                "created_date": "2024-02-05",
                "updated_date": "2026-06-30",
                "estimated_cost": 67500000.00,
                "actual_cost": 62800000.00,
                "district": "Chattogram",
                "upazila": "Sadar", "station": "CTG-03",
                "division": "Chattogram",
                "sor_agency": "LGED",
                "zone": "C",
                "sor_rates": {
                    "zone_a": 980.00,
                    "zone_b": 1050.00,
                    "zone_c": 1180.00,
                    "zone_d": 1130.00
                },
                "documents": []
            }
        ]
    },
    "cross_references": {
        "last_updated": "2026-06-30T00:00:00Z",
        "references": [
            {
                "package_no": "BWDB-CTG-01/2024-25",
                "tender_ids": ["1290886"],
                "award_ids": ["1012345"],
                "project_ids": ["BWDB-2024-001"],
                "contracts": ["contract-1"],
                "status": "active",
                "relations": [
                    {
                        "type": "tender_to_project",
                        "source_id": "1290886",
                        "target_id": "BWDB-2024-001",
                        "mapping_type": "e_gp_to_bwdb"
                    },
                    {
                        "type": "project_to_award",
                        "source_id": "BWDB-2024-001",
                        "target_id": "1012345",
                        "mapping_type": "bwdb_to_award"
                    }
                ]
            }
        ]
    },
    "lifecycles": {
        "last_updated": "2026-06-30T00:00:00Z",
        "lifecycles": [
            {
                "lifecycle_id": "lifecycle-1290886",
                "tender_id": "1290886",
                "package_no": "BWDB-CTG-01/2024-25",
                "project_id": "BWDB-2024-001",
                "award_id": "1012345",
                "contractor_id": "CON-001",
                "stages": [
                    {
                        "stage": "planning",
                        "stage_id": "stage-1",
                        "status": "completed",
                        "start_date": "2024-01-15",
                        "end_date": "2024-02-15",
                        "actions": [
                            {"action": "tender_publication", "completed_at": "2024-01-15"},
                            {"action": "bid_submission_deadline", "completed_at": "2024-02-15"},
                            {"action": "bid_opening", "completed_at": "2024-02-20"},
                            {"action": "contract_award", "completed_at": "2024-02-28"}
                        ]
                    },
                    {
                        "stage": "implementation",
                        "stage_id": "stage-2",
                        "status": "in_progress",
                        "start_date": "2024-03-15",
                        "end_date": "2025-02-28",
                        "actions": [
                            {"action": "site_preparation", "completed_at": "2024-04-30"},
                            {"action": "design_execution", "completed_at": "2024-09-30"},
                            {"action": "construction", "completed_at": None, "progress_percentage": 65},
                            {"action": "testing", "completed_at": None, "progress_percentage": 40}
                        ]
                    },
                    {
                        "stage": "handover",
                        "stage_id": "stage-3",
                        "status": "pending",
                        "start_date": "2025-03-01",
                        "end_date": "2025-06-30",
                        "actions": [
                            {"action": "final_inspection", "completed_at": None},
                            {"action": "punch_list", "completed_at": None},
                            {"action": "closeout", "completed_at": None}
                        ]
                    }
                ],
                "budgets": [
                    {"category": "labor", "allocated": 15000000.00, "spent": 12000000.00, "remaining": 3000000.00},
                    {"category": "materials", "allocated": 20000000.00, "spent": 18500000.00, "remaining": 1500000.00},
                    {"category": "equipment", "allocated": 8000000.00, "spent": 7000000.00, "remaining": 1000000.00},
                    {"category": "overhead", "allocated": 4500000.00, "spent": 4300000.00, "remaining": 200000.00}
                ],
                "documents": [
                    {"id": "lifecycle-doc-1", "title": "Project Timeline", "type": "timeline", "url": "/lifecycles/1/documents/timeline.pdf"},
                    {"id": "lifecycle-doc-2", "title": "Budget Tracking", "type": "budget", "url": "/lifecycles/1/documents/budget.xlsx"}
                ]
            }
        ]
    }
}

# ── Helpers ────────────────────────────────────────────────────────────

async def _query_tenders(db: AsyncSession, agency: Optional[str] = None,
                          search: Optional[str] = None,
                          limit: int = 50,
                          identifier: Optional[str] = None) -> List[dict]:
    """Query procurement_tenders from DB with optional filters."""
    sql = """
        WITH selected AS (
            SELECT pt.id, pt.package_no, pt.title, pt.agency_code,
                   pt.match_type, pt.created_at
            FROM procurement_tenders pt
            WHERE 1=1
    """
    params = {}
    if agency:
        sql += " AND pt.agency_code = :agency"
        params["agency"] = agency
    if search:
        sql += " AND (pt.title ILIKE :search OR pt.package_no ILIKE :search)"
        params["search"] = f"%{search}%"
    if identifier:
        sql += " AND (pt.id::text = :identifier OR pt.package_no = :identifier)"
        params["identifier"] = identifier
    sql += """
            ORDER BY pt.created_at DESC NULLS LAST
            LIMIT :limit
        )
        SELECT selected.id, selected.package_no, selected.title,
               selected.title AS description, selected.agency_code,
               COALESCE(app.estimated_cost_bdt, live.estimated_value_bdt, 0)
                   AS estimated_amount_bdt,
               COALESCE(live.deadline, app.deadline) AS closing_date,
               COALESCE(live.status, app.status, selected.match_type) AS status,
               selected.created_at,
               NULL::text AS division,
               award.district
        FROM selected
        LEFT JOIN app_records app
          ON app.procurement_tender_id = selected.id::text
        LEFT JOIN live_tender_sources live
          ON live.procurement_tender_id = selected.id::text
        LEFT JOIN LATERAL (
            SELECT ar.district
            FROM award_records_v2 ar
            WHERE ar.procurement_tender_id = selected.id::text
            ORDER BY ar.created_at DESC NULLS LAST
            LIMIT 1
        ) award ON TRUE
        ORDER BY selected.created_at DESC NULLS LAST
    """
    params["limit"] = limit
    result = await db.execute(text(sql), params)
    return [dict(r) for r in result.mappings().all()]


# Government portal API endpoints
@router.get("/bppa/tenders", response_model=GovernmentPortalResponse)
async def get_bppa_tenders(
    filters: PortalFilters = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """Get tenders from BPPA OCDS API — backed by procurement_tenders table."""
    try:
        rows = await _query_tenders(db, search=filters.search, limit=100)
        if not rows:
            data = GOVERNMENT_DATA["bppa_ocds"]
            return {
                "success": True, "source": "bppa_ocds_fallback",
                "last_updated": data["last_updated"],
                "count": len(data["releases"]), "data": data["releases"],
            }

        releases = []
        for row in rows:
            releases.append({
                "ocid": f"ocds-{row.get('id', 'unknown')}",
                "id": f"tender-{row.get('id', 'unknown')}",
                "date": row.get("created_at", ""),
                "release_type": "tender",
                "parties": [{"id": "party-1", "name": row.get("agency_code", "Unknown"), "type": "procuringEntity"}],
                "tender": {
                    "title": row.get("title", ""),
                    "description": row.get("description", ""),
                    "status": row.get("status", "active"),
                    "procurementMethod": "open",
                    "value": {"amount": float(row.get("estimated_amount_bdt") or 0), "currency": "BDT"},
                    "submissionDeadline": str(row.get("closing_date", "")),
                },
                "contracts": None,
                "amendments": None,
            })

        # Apply date filters client-side
        if filters.start_date:
            releases = [r for r in releases if r.get("date") and r["date"] >= str(filters.start_date)]
        if filters.end_date:
            releases = [r for r in releases if r.get("date") and r["date"] <= str(filters.end_date)]

        return {
            "success": True, "source": "procurement_tenders",
            "last_updated": datetime.utcnow().isoformat(),
            "count": len(releases), "data": releases,
        }
    except Exception as e:
        logger.error(f"Error fetching BPPA tenders: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching BPPA tenders: {str(e)}")

@router.get("/bppa/tenders/{tender_id}", response_model=SuccessWithData)
async def get_bppa_tender_by_id(tender_id: str):
    """Get specific tender from BPPA OCDS API by ID."""
    try:
        data = GOVERNMENT_DATA["bppa_ocds"]
        
        # Find release by tender_id (match in contracts or tender)
        release = None
        for r in data["releases"]:
            if r.get("tender", {}).get("id") == tender_id or r.get("id") == tender_id:
                release = r
                break
        
        if not release:
            raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found in BPPA OCDS")
        
        return {
            "success": True,
            "source": "bppa_ocds",
            "tender_id": tender_id,
            "data": OCDSRelease(**release).dict()
        }
        
    except Exception as e:
        logger.error(f"Error fetching BPPA tender {tender_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching BPPA tender: {str(e)}")

@router.get("/bwdb/projects", response_model=GovernmentPortalResponse)
async def get_bwdb_projects(
    filters: PortalFilters = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """Get BWDB projects from procurement_tenders table."""
    try:
        rows = await _query_tenders(db, agency="BWDB", search=filters.search, limit=100)
        if not rows:
            data = GOVERNMENT_DATA["bwdb_projects"]
            return {"success": True, "source": "bwdb_api_fallback",
                    "last_updated": data["last_updated"],
                    "count": len(data["projects"]), "data": data["projects"]}
        return {"success": True, "source": "procurement_tenders",
                "last_updated": datetime.utcnow().isoformat(),
                "count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"Error fetching BWDB projects: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching BWDB projects: {str(e)}")

@router.get("/bwdb/projects/{project_id}", response_model=SuccessWithData)
async def get_bwdb_project_by_id(
    project_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Get specific BWDB project from procurement_tenders by ID."""
    try:
        rows = await _query_tenders(db, agency="BWDB", identifier=project_id, limit=1)
        row = rows[0] if rows else None
        if not row:
            raise HTTPException(status_code=404, detail=f"BWDB project {project_id} not found")
        return {"success": True, "source": "procurement_tenders",
                "project_id": project_id, "data": row}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching BWDB project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pwd/projects", response_model=GovernmentPortalResponse)
async def get_pwd_projects(
    filters: PortalFilters = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """Get PWD projects from procurement_tenders table."""
    try:
        rows = await _query_tenders(db, agency="PWD", search=filters.search, limit=100)
        if not rows:
            data = GOVERNMENT_DATA["pwd_projects"]
            return {"success": True, "source": "pwd_api_fallback",
                    "last_updated": data["last_updated"],
                    "count": len(data["projects"]), "data": data["projects"]}
        return {"success": True, "source": "procurement_tenders",
                "last_updated": datetime.utcnow().isoformat(),
                "count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"Error fetching PWD projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lged/projects", response_model=GovernmentPortalResponse)
async def get_lged_projects(
    filters: PortalFilters = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """Get LGED projects from procurement_tenders table."""
    try:
        rows = await _query_tenders(db, agency="LGED", search=filters.search, limit=100)
        if not rows:
            data = GOVERNMENT_DATA["lged_projects"]
            return {"success": True, "source": "lged_api_fallback",
                    "last_updated": data["last_updated"],
                    "count": len(data["projects"]), "data": data["projects"]}
        return {"success": True, "source": "procurement_tenders",
                "last_updated": datetime.utcnow().isoformat(),
                "count": len(rows), "data": rows}
    except Exception as e:
        logger.error(f"Error fetching LGED projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cross-reference", response_model=SuccessWithData)
async def get_cross_reference(
    package_no: str = Query(..., description="Package number to lookup"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get cross-portal references for a package number from procurement tables."""
    try:
        result = await db.execute(
            text(
                """
                SELECT pt.id, pt.package_no, pt.title, pt.agency_code,
                       COALESCE(live.status, app.status, pt.match_type) AS status,
                       COALESCE(app.estimated_cost_bdt, live.estimated_value_bdt, 0)
                           AS estimated_amount_bdt
                FROM procurement_tenders pt
                LEFT JOIN app_records app
                  ON app.procurement_tender_id = pt.id::text
                LEFT JOIN live_tender_sources live
                  ON live.procurement_tender_id = pt.id::text
                WHERE pt.package_no = :pkg
                LIMIT 1
                """
            ),
            {"pkg": package_no}
        )
        row = result.mappings().first()
        if row:
            return {
                "success": True, "package_no": package_no,
                "source": "procurement_tenders",
                "last_updated": datetime.utcnow().isoformat(),
                "references": {
                    "package_no": package_no,
                    "tender_ids": [row["id"]],
                    "status": row["status"],
                    "agency": row["agency_code"],
                    "estimated_cost": float(row["estimated_amount_bdt"] or 0),
                }
            }
        raise HTTPException(status_code=404, detail=f"Package {package_no} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cross-reference: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lifecycle", response_model=GovernmentPortalResponse)
async def get_procurement_lifecycle(
    tender_id: Optional[str] = Query(None, description="Tender ID"),
    project_id: Optional[str] = Query(None, description="Project ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get procurement lifecycle from procurement_lifecycle table."""
    try:
        lookup = tender_id or project_id
        if not lookup:
            raise HTTPException(status_code=400, detail="tender_id or project_id required")
        result = await db.execute(
            text(
                """
                SELECT id, tender_id, package_no, agency_code, zone_name, title,
                       estimated_cost_bdt, award_amount_bdt, npp_ratio, winner,
                       award_date, procurement_method, pe_office, match_type,
                       data_source, created_at, updated_at
                FROM procurement_lifecycle
                WHERE tender_id = :id OR id::text = :id OR package_no = :id
                LIMIT 10
                """
            ),
            {"id": lookup}
        )
        rows = [dict(r) for r in result.mappings().all()]
        if not rows:
            raise HTTPException(status_code=404, detail="Lifecycle not found")
        return {"success": True, "source": "procurement_lifecycle",
                "last_updated": datetime.utcnow().isoformat(),
                "count": len(rows), "data": rows}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lifecycle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/organizations", response_model=PortalOrganizationsResponse)
async def get_organizations():
    """Get government agency organizations."""
    organizations = [
        {"id": "bwdb", "name": "BWDB", "type": "federal", "division": "All", "zone": "ALL"},
        {"id": "pwd", "name": "PWD", "type": "federal", "division": "All", "zone": "ALL"},
        {"id": "lged", "name": "LGED", "type": "federal", "division": "All", "zone": "ALL"},
        {"id": "bpdb", "name": "BPDB", "type": "federal", "division": "All", "zone": "ALL"},
        {"id": "rhd", "name": "RHD", "type": "federal", "division": "All", "zone": "ALL"},
        {"id": "bb", "name": "BBA", "type": "federal", "division": "All", "zone": "ALL"},
        {"id": "bpdb_territory", "name": "BPDB Territory", "type": "territory", "zone": "ALL"},
        {"id": "lgd", "name": "LGD", "type": "municipal", "zone": "ALL"},
        {"id": "waru", "name": "WARU", "type": "semi_government", "zone": "ALL"},
        {"id": "cbdrm", "name": "CBDRM", "type": "semi_government", "zone": "ALL"}
    ]
    
    return {
        "success": True,
        "source": "gov_portal_meta",
        "count": len(organizations),
        "data": organizations
    }

@router.get("/zones", response_model=PortalZonesResponse)
async def get_zones():
    """Get zone information for government agency projects.

    Source: BWDB Standard Schedule of Rates-2022, PWD SoR 2022, LGED SoR.

    Zone mapping per agency (C/D swapped between LGED vs BWDB/PWD):
      BWDB Zone C = South-Western + Southern + Western + Eastern (44 districts)
      LGED Zone C = Rajshahi, Rangpur Division (BWDB/PWD Zone D)
      BWDB/PWD Zone D = Northern + North-Western (Rajshahi, Rangpur)
      LGED Zone D = Khulna, Barishal Division (BWDB/PWD Zone C)
    """
    zones = [
        {
            "code": "A",
            "name": "Zone A — Central",
            "agency": "BWDB",
            "divisions": ["Dhaka", "Mymensingh"],
            "districts": [
                "Dhaka", "Narayanganj", "Manikganj", "Narshingdi", "Gazipur",
                "Mymensingh", "Munsiganj", "Kishoreganj", "Tangail",
                "Jamalpur", "Sherpur", "Netrakona"
            ],
            "agencies": ["BWDB", "PWD", "LGED"],
            "description": "Central zone covering Dhaka and Mymensingh divisions (12 districts)"
        },
        {
            "code": "B",
            "name": "Zone B — South-Eastern & North-Eastern",
            "agency": "BWDB",
            "divisions": ["Chattogram", "Sylhet"],
            "districts": [
                "Chattogram", "Rangamati", "Khagrachori", "Cox's Bazar", "Bandarban",
                "Sylhet", "Sunamganj", "Hobiganj", "Moulvibazar"
            ],
            "agencies": ["BWDB", "PWD", "LGED"],
            "description": "South-Eastern (Chattogram) + North-Eastern (Sylhet) zones — 9 districts"
        },
        {
            "code": "C",
            "name": "Zone C — South-Western / Southern / Western / Eastern (BWDB)",
            "agency": "BWDB",
            "divisions": ["Khulna", "Barishal", "Faridpur", "Cumilla"],
            "districts": [
                "Khulna", "Satkhira", "Bagerhat", "Jashore", "Norail",
                "Barishal", "Jhalkathi", "Pirojpur", "Patuakhali", "Barguna", "Bhola",
                "Faridpur", "Rajbari", "Madaripur", "Shariatpur", "Gopalganj",
                "Kushtia", "Chuadanga", "Meherpur", "Magura", "Jhenaidah",
                "Cumilla", "Brahmanbaria", "Chandpur", "Feni", "Noakhali", "Lakshmipur"
            ],
            "agencies": ["BWDB", "PWD"],
            "lged_zone": "D",
            "lged_districts": [
                "Khulna", "Satkhira", "Bagerhat", "Jashore", "Norail",
                "Barishal", "Jhalkathi", "Pirojpur", "Patuakhali", "Barguna", "Bhola"
            ],
            "lged_note": "LGED maps these districts to Zone D (C↔D swap)",
            "description": "BWDB Zone C: 27 districts across South-Western, Southern, Western, and Eastern zones. LGED maps to Zone D."
        },
        {
            "code": "D",
            "name": "Zone D — Northern & North-Western (BWDB)",
            "agency": "BWDB",
            "divisions": ["Rangpur", "Rajshahi"],
            "districts": [
                "Rangpur", "Kurigram", "Gaibandha", "Lalmonirhat",
                "Nilphamari", "Thakurgaon", "Panchagarh", "Dinajpur",
                "Rajshahi", "Naogaon", "Nawabganj", "Natore",
                "Bogura", "Jaipurhat", "Sirajganj", "Pabna"
            ],
            "agencies": ["BWDB", "PWD"],
            "lged_zone": "C",
            "lged_districts": [
                "Rangpur", "Kurigram", "Gaibandha", "Lalmonirhat",
                "Nilphamari", "Thakurgaon", "Panchagarh", "Dinajpur",
                "Rajshahi", "Naogaon", "Nawabganj", "Natore",
                "Bogura", "Jaipurhat", "Sirajganj", "Pabna"
            ],
            "lged_note": "LGED maps these districts to Zone C (C↔D swap)",
            "description": "BWDB Zone D: 16 districts across Northern and North-Western zones. LGED maps to Zone C."
        }
    ]
    
    return {
        "success": True,
        "source": "gov_portal_meta",
        "count": len(zones),
        "data": zones
    }

@router.get("/health", response_model=PortalHealthResponse)
async def health_check():
    """Health check endpoint for government portal integration."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "government_portal_apis": {
            "bppa_ocds": "active",
            "bwdb_project_api": "active",
            "pwd_project_api": "active",
            "lged_project_api": "active",
            "cross_reference": "active",
            "lifecycle": "active",
            "organizations": "active",
            "zones": "active"
        },
        "total_sources": 8,
        "data_records": sum([
            len(GOVERNMENT_DATA["bppa_ocds"]["releases"]),
            len(GOVERNMENT_DATA["bwdb_projects"]["projects"]),
            len(GOVERNMENT_DATA["pwd_projects"]["projects"]),
            len(GOVERNMENT_DATA["lged_projects"]["projects"]),
            len(GOVERNMENT_DATA["cross_references"]["references"]),
            len(GOVERNMENT_DATA["lifecycles"]["lifecycles"])
        ])
    }
