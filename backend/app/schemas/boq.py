'''
BOQ schemas - FIXED to match frontend expectations
'''

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class BoqItem(BaseModel):
    '''
    BOQ Item - EXACT frontend match for frontend_v2/src/entities/boq/types.ts
    
    Frontend expects these exact field names:
    - item_no (not item_code)
    - code (alternative to item_no) 
    - desc (not description)
    - qty (not quantity)
    - rate (not quoted_rate)
    - diff (not pct_diff)
    - pct_diff
    - flag
    - section
    - sor_source
    '''
    item_no: Optional[str] = Field(None, description="Item number")
    code: Optional[str] = Field(None, description="Item code (alternative to item_no)")
    agency: Optional[str] = Field(None, description="Agency")
    work_type: Optional[str] = Field(None, description="Work type")
    desc: str = Field(..., description="Description (frontend expects: desc, not: description)")
    unit: str = Field(..., description="Unit")
    qty: int = Field(..., description="Quantity (frontend expects: qty, not: quantity)")
    rate: Optional[Decimal] = Field(None, description="BOQ rate (frontend expects: rate, not: quoted_rate)")
    sor_rate: Optional[Decimal] = Field(None, description="SOR rate")
    diff: Optional[float] = Field(None, description="Difference (frontend expects: diff, not: pct_diff)")
    pct_diff: Optional[float] = Field(None, description="Percentage difference")
    flag: Optional[str] = Field(None, description="Flag")
    section: Optional[str] = Field(None, description="Section")
    sor_source: Optional[str] = Field(None, description="SOR source")
    
    # Backend internal fields for data mapping
    # NOT included in frontend response but kept for backend internal use
    id: Optional[str] = None
    description: Optional[str] = None  # Backend internal field
    quantity: Optional[int] = None     # Backend internal field
    quoted_rate: Optional[Decimal] = None  # Backend internal field


class BoqSummary(BaseModel):
    '''
    BOQ Summary - EXACT frontend match for frontend_v2/src/entities/boq/types.ts
    
    Frontend expects:
    - by_work_type: any[]
    - total_sor: number
    - total_quoted: number  
    - discount_pct: number
    '''
    by_work_type: Optional[List[Any]] = Field(default_factory=list)
    total_sor: Decimal = Field(default=0, description="Total SOR amount")
    total_quoted: Decimal = Field(default=0, description="Total BOQ amount")
    discount_pct: float = Field(default=0, description="Discount percentage")


class BoqComparisonResult(BaseModel):
    '''
    BOQ Comparison Result - EXACT frontend match for frontend_v2/src/entities/boq/types.ts
    '''
    success: bool = Field(..., description="Success status")
    comparison_id: Optional[str] = Field(None, description="Comparison ID")
    boq_file_id: Optional[str] = Field(None, description="BOQ file ID")
    sor_agency: Optional[str] = Field(None, description="SOR agency")
    zone: Optional[str] = Field(None, description="Zone")
    
    # 🚨 FRONTEND EXPECTS: items: BoqItem[] (not data)
    items: List[BoqItem] = Field(default_factory=list, description="BOQ items (frontend expects: items, not: data)")
    
    summary: BoqSummary = Field(..., description="BOQ summary")
    flagged: Optional[List[Any]] = Field(default_factory=list)
    total_items: Optional[int] = Field(None, description="Total items")
    mismatches: Optional[int] = Field(None, description="Mismatch count")
    variances: Optional[int] = Field(None, description="Variance count")
    matches: Optional[int] = Field(None, description="Match count")
    below_sor: Optional[int] = Field(None, description="Below SOR count")
    excel_path: Optional[str] = Field(None, description="Excel file path")
    docx_path: Optional[str] = Field(None, description="DOCX file path")
    tenderai_dir: Optional[str] = Field(None, description="TenderAI directory")
    created_at: Optional[str] = Field(None, description="Created timestamp")
    financial_check: Optional[List[Any]] = Field(None, description="Financial check data")
    estimated_cost_app: Optional[Decimal] = Field(None, description="Estimated cost app")


# BACKWARDS COMPATIBILITY - Legacy compatibility
class LegacyBoqResponse(BaseModel):
    '''Legacy BOQ response for backwards compatibility'''
    success: bool = Field(..., description="Success status")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Legacy data format")
    summary: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Legacy summary format")


# Schema classes for API
class BOQItemRead(BoqItem):
    """BOQ Item read schema"""
    pass


class BOQComparisonCreate(BaseModel):
    """BOQ Comparison create schema"""
    tender_id: Optional[str] = None
    boq_file_id: str
    sor_agency: str = "BWDB"
    zone: Optional[str] = None
    total_items: int = 0
    matches: int = 0
    variances: int = 0
    mismatches: int = 0
    below_sor: int = 0
    total_sor_amount: Optional[float] = None
    total_quoted_amount: Optional[float] = None
    discount_pct: Optional[float] = None
    summary_by_work_type: Dict[str, Any] = {}
    excel_path: Optional[str] = None
    docx_path: Optional[str] = None
    tenderai_dir: Optional[str] = None


class BOQComparisonRead(BOQComparisonCreate):
    """BOQ Comparison read schema"""
    id: str
    user_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class BOQJobStatusRead(BaseModel):
    """BOQ Job Status read schema"""
    id: str
    user_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str