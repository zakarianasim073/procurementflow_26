"""SOR API routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import get_optional_user
from app.schemas.response_models import (
    SORAgenciesResponse,
    SORBatchResponse,
    SORLoadPdfResponse,
    SORRateLookup,
    SORReimportResponse,
)
from app.sor.sor_service import sor_service

router = APIRouter(prefix="/sor", tags=["sor"])


@router.get("/agencies", response_model=SORAgenciesResponse)
async def list_sor_agencies(
    user: dict = Depends(get_optional_user),
):
    """List available SOR agencies with stats"""
    agencies = []
    for agency in ['BWDB', 'PWD', 'LGED']:
        stats = sor_service.get_stats(agency)
        agencies.append({
            "id": agency.lower(),
            "name": agency,
            "total_rates": stats["total_rates"],
            "has_csv": stats["has_csv"],
        })
    return {"agencies": agencies}


@router.get("/lookup", response_model=SORRateLookup)
async def lookup_sor_rate(
    code: str = Query(..., description="Item code to look up"),
    agency: str = Query("BWDB", pattern="^(BWDB|PWD|LGED)$"),
    zone: Optional[str] = Query(None, pattern="^(A|B|C|D)$"),
    description: Optional[str] = Query(None),
    user: dict = Depends(get_optional_user),
):
    """Look up a single SOR rate by code"""
    rate, record = sor_service.find_rate(code, description or "", agency, zone)
    if rate is None:
        raise HTTPException(status_code=404, detail="Rate not found")
    
    return {
        "code": record.code,
        "description": record.description,
        "unit": record.unit,
        "zone_a": record.zone_a,
        "zone_b": record.zone_b,
        "zone_c": record.zone_c,
        "zone_d": record.zone_d,
        "rate": rate,
        "zone": zone or "A",
        "agency": agency,
    }


@router.post("/load-pdf", response_model=SORLoadPdfResponse)
async def load_sor_from_pdf(
    agency: str = Query(..., pattern="^(BWDB|PWD|LGED)$"),
    zone: Optional[str] = Query(None, pattern="^(A|B|C|D)$"),
    file: Optional[str] = Query(None, description="Path to PDF file"),
    user: dict = Depends(get_optional_user),
):
    """Load SOR rates from PDF file"""
    if not file:
        raise HTTPException(status_code=400, detail="PDF file path required")
    
    pdf_path = Path(file)
    if not pdf_path.exists():
        # Try relative to base dir
        pdf_path = Path(settings.BASE_DIR) / "uploads" / file
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
    
    loaded = sor_service.load_from_pdf(agency, str(pdf_path), zone)
    return {"success": True, "loaded": loaded, "agency": agency}


class BatchLookupRequest(BaseModel):
    codes: List[str] = Field(..., description="List of item codes to look up")
    descriptions: List[str] = Field(default_factory=list, description="Corresponding descriptions (for fuzzy fallback)")
    agency: str = Field("BWDB", pattern="^(BWDB|PWD|LGED)$")
    zone: Optional[str] = Field(None, pattern="^(A|B|C|D)$")


class SorCompareRequest(BaseModel):
    codes: List[str] = Field(..., description="List of SOR item codes to compare across agencies")
    agencies: List[str] = Field(..., description="List of agencies to compare (BWDB, PWD, LGED)")


class SorCompareItem(BaseModel):
    code: str
    agency: str
    matched: bool
    rate: Optional[float] = None
    description: str = ""
    unit: str = ""
    zone_a: Optional[float] = None
    zone_b: Optional[float] = None
    zone_c: Optional[float] = None
    zone_d: Optional[float] = None


@router.post("/batch-lookup", response_model=SORBatchResponse)
async def batch_lookup_sor_rates(
    request: BatchLookupRequest,
    user: dict = Depends(get_optional_user),
):
    """Look up multiple SOR rates in a single call."""
    if not request.codes:
        raise HTTPException(status_code=400, detail="codes list is required")
    descs = list(request.descriptions)
    if len(descs) < len(request.codes):
        descs.extend([""] * (len(request.codes) - len(descs)))
    elif len(descs) > len(request.codes):
        descs = descs[:len(request.codes)]
    results = sor_service.batch_find_rates(
        request.codes, descs, request.agency, request.zone,
    )
    items = []
    for code, result in zip(request.codes, results):
        if result is None:
            items.append({"code": code, "matched": False, "rate": None})
        else:
            rate, record = result
            items.append({
                "code": code,
                "matched": True,
                "rate": rate,
                "matched_code": record.code,
                "description": record.description,
                "unit": record.unit,
                "agency": request.agency,
                "zone": request.zone or "A",
            })
    return {"results": items, "total": len(items), "matched": sum(1 for i in items if i["matched"])}


@router.post("/compare")
async def compare_sor_across_agencies(
    request: SorCompareRequest,
    user: dict = Depends(get_optional_user),
):
    """Compare SOR rates for the same codes across multiple agencies."""
    results = []
    for agency in request.agencies:
        for code in request.codes:
            rate, record = sor_service.find_rate(code, "", agency, None)
            if rate is not None and record:
                results.append(SorCompareItem(
                    code=code, agency=agency, matched=True,
                    rate=rate, description=record.description,
                    unit=record.unit,
                    zone_a=record.zone_a, zone_b=record.zone_b,
                    zone_c=record.zone_c, zone_d=record.zone_d,
                ))
            else:
                results.append(SorCompareItem(
                    code=code, agency=agency, matched=False,
                ))
    return results


@router.get("/reimport", response_model=SORReimportResponse)
async def reimport_sor_from_csv(
    force: bool = Query(False, description="Truncate and re-import all SOR data"),
    user: dict = Depends(get_optional_user),
):
    """Re-import SOR rates from CSV files into PostgreSQL.
    
    By default skips if data exists; use force=True to truncate and re-import.
    """
    from app.services.sor_etl import import_sor_to_db
    result = import_sor_to_db(force=force)
    return {"success": True, "result": result}
