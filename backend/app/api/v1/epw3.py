"""e-PW3 Forms API — BPPA Standard Tender Document Auto-Generation"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from app.core.security import get_current_user, get_optional_user
from app.services.epw3_forms import epw3_generator, EPW3_FORMS
from pydantic import BaseModel as _PydanticBaseModel


class EPW3FormsListResponse(_PydanticBaseModel):
    success: bool = True
    total: int = 0
    forms: List[Dict[str, Any]] = []

class EPW3GenerateResponse(_PydanticBaseModel):
    success: bool = True
    data: Dict[str, Any] = {}

class EPW3FormDetailResponse(_PydanticBaseModel):
    success: bool = True
    form: Dict[str, Any] = {}

class EPW3TenderFormsResponse(_PydanticBaseModel):
    success: bool = True
    tender_id: str = ""
    forms: Optional[List[Dict[str, Any]]] = []
    has_forms: bool = False
    total_forms: Optional[int] = None
    form_ids: Optional[List[str]] = []
    generated_at: Optional[str] = None

router = APIRouter(prefix="/epw3", tags=["epw3"])


class EPW3GenerateRequest(BaseModel):
    tender_id: str
    company: Dict[str, Any]
    tender_info: Dict[str, Any]
    bid_amount: float
    personnel: Optional[List[Dict]] = None
    jv_partners: Optional[List[Dict]] = None
    ongoing_projects: Optional[List[Dict]] = None


@router.get("/forms", response_model=EPW3FormsListResponse)
async def list_epw3_forms():
    """List all available e-PW3 forms with descriptions."""
    return {
        "success": True,
        "total": len(EPW3_FORMS),
        "forms": [
            {
                "form_id": fid,
                "title": info["title"],
                "mandatory": info["mandatory"],
            }
            for fid, info in EPW3_FORMS.items()
        ],
    }


@router.post("/generate", response_model=EPW3GenerateResponse)
async def generate_epw3_forms(
    req: EPW3GenerateRequest,
    user: dict = Depends(get_optional_user),
):
    """Generate all applicable e-PW3 forms for a tender."""
    try:
        result = await epw3_generator.generate_all(
            tender_id=req.tender_id,
            company=req.company,
            tender_info=req.tender_info,
            bid_amount=req.bid_amount,
            personnel=req.personnel,
            jv_partners=req.jv_partners,
            ongoing_projects=req.ongoing_projects,
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"e-PW3 generation failed: {str(e)}")


@router.get("/form/{form_id}", response_model=EPW3FormDetailResponse)
async def get_epw3_form(
    form_id: str,
    tender_id: str,
    user: dict = Depends(get_optional_user),
):
    """Get a specific e-PW3 form for a tender."""
    from app.db.base import get_session_factory
    from app.models.intelligence import EPW3FormRecord
    from sqlalchemy import select
    
    sf = get_session_factory()
    async with sf() as session:
        stmt = select(EPW3FormRecord).where(EPW3FormRecord.tender_id == tender_id)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        
    if not record:
        raise HTTPException(status_code=404, detail="e-PW3 data not found — generate first")
    
    form = record.forms.get(form_id)
    if not form:
        raise HTTPException(status_code=404, detail=f"Form {form_id} not found for tender {tender_id}")
    
    return {"success": True, "form": form}


@router.get("/list/{tender_id}", response_model=EPW3TenderFormsResponse)
async def list_tender_forms(
    tender_id: str,
    user: dict = Depends(get_optional_user),
):
    """List all generated e-PW3 forms for a tender."""
    from app.db.base import get_session_factory
    from app.models.intelligence import EPW3FormRecord
    from sqlalchemy import select
    
    sf = get_session_factory()
    async with sf() as session:
        stmt = select(EPW3FormRecord).where(EPW3FormRecord.tender_id == tender_id)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        
    if not record:
        return {"success": True, "tender_id": tender_id, "forms": [], "has_forms": False}
    
    return {
        "success": True,
        "tender_id": tender_id,
        "has_forms": True,
        "total_forms": record.total_forms,
        "form_ids": record.form_ids,
        "generated_at": record.generated_at,
    }
