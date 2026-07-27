"""Tender Submission Documents API — Auto-generate Equipment, Manpower, Methodology, JV Deed, Credit Line, BG from TDS data"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from pathlib import Path
import os
import logging

from app.core.config import settings
from app.core.security import get_optional_user

router = APIRouter(prefix="/tender-docs", tags=["tender_docs"])

logger = logging.getLogger(__name__)


class TenderDocsGenerateRequest(BaseModel):
    tender_id: str
    contractor_id: Optional[str] = ""
    bidder_name: Optional[str] = ""
    bidder_address: Optional[str] = ""
    bidder_phone: Optional[str] = ""
    bidder_email: Optional[str] = ""
    bank_name: Optional[str] = ""
    bank_branch: Optional[str] = ""
    bank_address: Optional[str] = ""
    jv_partner_name: Optional[str] = ""
    jv_partner_address: Optional[str] = ""
    jv_share_1: Optional[str] = ""
    jv_share_2: Optional[str] = ""
    sor_agency: Optional[str] = ""
    zone: Optional[str] = ""

    # SLT Analysis params
    oce: Optional[float] = 0.0  # Official Cost Estimate
    nppi: Optional[float] = 0.891  # NPPI Index (default from e-GP)
    current_quote: Optional[float] = 0.0  # Your quoted amount
    assumed_bidders: Optional[int] = 8


DOC_NAMES = [
    "1_JV_DEED.docx",
    "2_Credit_Line.docx",
    "3_BG_Tender_Security.docx",
    "4_Equipment_Declaration.docx",
    "5_Manpower_Declaration.docx",
    "6_Methodology.docx",
]


def _find_tender_pdfs(tender_id: str) -> Dict[str, str]:
    """Find tender PDFs in tenders/ or uploads/ directories."""
    backend_root = Path(__file__).parent.parent.parent.parent  # backend/
    # Prefer individually acquired uploads (clean Notice/BOQ files), then fill
    # missing sections from consolidated runtime/tender storage.
    search_roots = [
        backend_root / "uploads" / tender_id,
        Path(settings.BASE_DIR) / "uploads" / tender_id,
        backend_root / "tenders" / tender_id,
        Path(settings.BASE_DIR) / "tenders" / tender_id,
    ]
    result: Dict[str, str] = {}
    for root in search_roots:
        if not root.exists():
            continue
        for f in root.iterdir():
            name = f.stem.lower()
            ext = f.suffix.lower()
            if ext not in (".pdf",):
                continue
            if "notice" in name or name == "1" or name.startswith("1."):
                result.setdefault("notice", str(f))
            elif "tds" in name and "2" in name:
                result.setdefault("tds_2", str(f))
            elif "tds" in name or name == "2" or name.startswith("2."):
                result.setdefault("tds", str(f))
            elif "boq" in name or name == "4" or name.startswith("4.") or name.startswith("3."):
                result.setdefault("boq", str(f))
    return result if result.get("notice") or result.get("tds") else {}


def _load_contractor(contractor_id: str) -> Dict[str, str]:
    """Load bidder name from contractors table. Address/contact not stored in DB."""
    from sqlalchemy import text
    from app.db.database import get_sync_session

    try:
        with get_sync_session() as session:
            row = session.execute(
                text("SELECT contractor_name FROM contractors WHERE id = :id OR contractor_name ILIKE :name LIMIT 1"),
                {"id": contractor_id, "name": f"%{contractor_id}%"},
            ).mappings().first()
            if row:
                return {"name": row["contractor_name"] or "", "address": "", "contact": ""}
    except Exception as e:
        logger.warning(f"Contractor lookup failed for {contractor_id}: {e}")
    return {}


def _build_tender_data(tender_id: str, extracted: Dict[str, Any], req: TenderDocsGenerateRequest) -> Dict[str, Any]:
    """Build comprehensive data dict for template filling from extracted variables + user input."""
    from app.services.template_filler import build_tender_template_data

    # Load contractor data if contractor_id provided
    contractor = {}
    if req.contractor_id:
        contractor = _load_contractor(req.contractor_id)

    bidder_name = req.bidder_name or contractor.get("name", "M/S. [Bidder Name]")
    bidder_address = req.bidder_address or contractor.get("address", "[Bidder Address]")
    bidder_phone = req.bidder_phone or contractor.get("contact", "[Phone]")

    data = build_tender_template_data(
        tender_data=extracted,
        bidder_name=bidder_name,
        bidder_address=bidder_address,
        bidder_phone=bidder_phone,
        bidder_email=req.bidder_email or "[Email]",
        bank_name=req.bank_name or "[Bank Name]",
        bank_branch=req.bank_branch or "[Branch]",
        bank_address=req.bank_address or "[Bank Address]",
        jv_name=f"{bidder_name} JV" if req.jv_partner_name else "",
        jv_partner2_name=req.jv_partner_name or "",
        jv_partner2_address=req.jv_partner_address or "",
        jv_share_1=req.jv_share_1 or "",
        jv_share_2=req.jv_share_2 or "",
    )
    return data, bidder_name, bidder_address, bidder_phone


@router.post("/generate")
async def generate_tender_docs(
    req: TenderDocsGenerateRequest,
    user: dict = Depends(get_optional_user),
):
    """Auto-generate all tender submission documents from extracted Notice/TDS data.

    Looks for tender PDFs in tenders/{tender_id}/ or uploads/{tender_id}/,
    extracts variables, and generates the complete client submission package:
    declarations, methodology, Work Plan and BOQ analysis (when BOQ data exists).
    """
    from app.services.tender_doc_generator import TenderDocGenerator, TenderPDFExtractor
    from app.services.tender_extractor import TenderExtractor
    from app.services.template_filler import build_tender_template_data

    tender_id = req.tender_id

    # Find PDFs
    pdfs = _find_tender_pdfs(tender_id)
    if not pdfs:
        exists_text = ""
        for root in [Path(settings.BASE_DIR) / "tenders" / tender_id, Path(settings.BASE_DIR) / "uploads" / tender_id]:
            if root.exists():
                exists_text = f" Found in {root}: {[f.name for f in root.iterdir()]}"
        raise HTTPException(
            status_code=404,
            detail=f"Tender {tender_id} PDFs not found in tenders/ or uploads/.{exists_text} Upload documents first via /api/tender/upload or run tender acquisition."
        )

    # Extract variables from Notice / TDS
    extracted = TenderExtractor().extract_all(
        notice_path=pdfs.get("notice"),
        tds_path=pdfs.get("tds"),
        tds_2_path=pdfs.get("tds_2"),
    )
    logger.info(f"Extracted variables for tender {tender_id}: {len(extracted)} keys, "
                f"personnel={len(extracted.get('eligibility', {}).get('personnel', []))}, "
                f"equipment={len(extracted.get('eligibility', {}).get('equipment', []))}")

    # Build TenderData using TenderDocGenerator's extractor for full data
    gen = TenderDocGenerator()
    tender_data = gen.extract_from_pdfs(
        notice_pdf=pdfs.get("notice", ""),
        tds_pdf=pdfs.get("tds", ""),
        boq_pdf=pdfs.get("boq", ""),
    )
    tender_data.tender_id = tender_data.tender_id or tender_id

    # Fill gaps from the PG17 tender pool. Acquired PDFs occasionally have
    # image-only Notice fields; the canonical pool remains keyed by tender ID.
    try:
        from sqlalchemy import text
        from app.db.database import get_sync_session
        with get_sync_session() as session:
            pool = session.execute(
                text("""
                    SELECT package_no, work_name, procuring_entity, pe_office,
                           closing_date, opening_date, tender_security_amount,
                           estimated_amount_bdt, completion_period_days,
                           required_equipment, required_personnel
                    FROM tender_data_pool
                    WHERE tender_id = :tender_id
                    ORDER BY created_at DESC NULLS LAST
                    LIMIT 1
                """),
                {"tender_id": tender_id},
            ).mappings().first()
        if pool:
            tender_data.package_no = tender_data.package_no or pool["package_no"] or ""
            tender_data.package_description = tender_data.package_description or pool["work_name"] or ""
            tender_data.procuring_entity = tender_data.procuring_entity or pool["procuring_entity"] or ""
            tender_data.organization = tender_data.organization or pool["pe_office"] or ""
            tender_data.tender_close_datetime = tender_data.tender_close_datetime or (str(pool["closing_date"]) if pool["closing_date"] else "")
            tender_data.tender_open_datetime = tender_data.tender_open_datetime or (str(pool["opening_date"]) if pool["opening_date"] else "")
            tender_data.tender_security_bdt = tender_data.tender_security_bdt or float(pool["tender_security_amount"] or 0)
            tender_data.estimated_value_bdt = tender_data.estimated_value_bdt or float(pool["estimated_amount_bdt"] or 0)
            tender_data.completion_period_days = tender_data.completion_period_days or int(pool["completion_period_days"] or 0)
            tender_data.equipment_list = tender_data.equipment_list or pool["required_equipment"] or []
            tender_data.manpower_list = tender_data.manpower_list or pool["required_personnel"] or []
    except Exception as exc:
        logger.warning("Tender pool enrichment failed for %s: %s", tender_id, exc)

    # Merge TenderExtractor's richer equipment/manpower lists
    eligibility = extracted.get("eligibility", {})
    if eligibility.get("equipment"):
        tender_data.equipment_list = eligibility["equipment"]
    if eligibility.get("personnel"):
        tender_data.manpower_list = eligibility["personnel"]

    # Build template data (unpacks bidder info from contractor DB or request)
    template_data, bidder_name, bidder_address, bidder_phone = _build_tender_data(tender_id, extracted, req)

    # Populate bidder info into TenderData for docx generator
    tender_data.bidder_name = bidder_name
    tender_data.bidder_address = bidder_address
    tender_data.bidder_phone = bidder_phone
    tender_data.bidder_email = req.bidder_email or "hbl.engr@gmail.com"
    tender_data.bank_name = req.bank_name or "[Bank Name]"
    tender_data.bank_branch = req.bank_branch or "[Branch]"
    tender_data.bank_address = req.bank_address or "[Bank Address]"

    # Generate the base forms plus Client No. 1's reference-layout package.
    backend_root = Path(__file__).parent.parent.parent.parent
    output_dir = str(backend_root / "outputs" / tender_id / "submission_docs")
    gen_results = gen.generate_all(tender_data, output_dir=output_dir)

    # Also generate via template_filler for template-based docs
    from app.services.template_filler import generate_all_tender_docs
    templates_dir = str(Path(__file__).parent.parent.parent / "services" / "templates")
    tf_results = {}
    if os.path.isdir(templates_dir):
        tf_results = generate_all_tender_docs(template_data, templates_dir, output_dir)

    # Generate SLT Analysis Excel if OCE provided
    slt_path = ""
    if req.oce and req.oce > 0:
        try:
            from app.services.slt_analysis import generate_slt_analysis
            slt_path = generate_slt_analysis(
                oce=req.oce,
                nppi=req.nppi or 0.891,
                current_quote=req.current_quote or 0,
                assumed_bidders=req.assumed_bidders or 8,
                output_path=os.path.join(output_dir, "7_SLT_Analysis.xlsx"),
                tender_info=extracted,
            )
        except Exception as e:
            logger.warning(f"SLT analysis failed: {e}")

    # Collect output files
    generated = []
    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath) and fname.endswith((".docx", ".xlsx")):
            size_kb = os.path.getsize(fpath) / 1024
            generated.append({
                "filename": fname,
                "path": fpath,
                "size_kb": round(size_kb, 1),
                "download_url": f"/api/tender-docs/{tender_id}/{fname}",
            })

    return {
        "success": True,
        "tender_id": tender_id,
        "generated_count": len(generated),
        "generated_files": generated,
        "doc_gen_status": gen_results,
        "slt_analysis": slt_path,
        "extracted_data": {
            "tender_id": extracted.get("tender_id", tender_id),
            "package_no": extracted.get("package_no", ""),
            "procuring_entity": extracted.get("procuring_entity", ""),
            "estimated_cost": extracted.get("estimated_cost", ""),
            "tender_security": extracted.get("tender_security", ""),
            "personnel_count": len(extracted.get("eligibility", {}).get("personnel", [])),
            "equipment_count": len(extracted.get("eligibility", {}).get("equipment", [])),
        },
    }


@router.get("/{tender_id}/list")
async def list_tender_docs(
    tender_id: str,
    user: dict = Depends(get_optional_user),
):
    """List all generated submission documents for a tender."""
    backend_root = Path(__file__).parent.parent.parent.parent
    output_dir = backend_root / "outputs" / tender_id / "submission_docs"
    if not output_dir.exists():
        return {
            "success": True,
            "tender_id": tender_id,
            "generated": [],
            "has_docs": False,
        }

    files = []
    for f in sorted(output_dir.iterdir()):
        if f.is_file() and f.suffix in (".docx", ".xlsx"):
            files.append({
                "filename": f.name,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "download_url": f"/api/tender-docs/{tender_id}/{f.name}",
            })

    return {
        "success": True,
        "tender_id": tender_id,
        "has_docs": len(files) > 0,
        "generated": files,
    }


@router.get("/{tender_id}/{doc_name:path}")
async def download_tender_doc(
    tender_id: str,
    doc_name: str,
    user: dict = Depends(get_optional_user),
):
    """Download a specific generated submission document."""
    backend_root = Path(__file__).parent.parent.parent.parent
    base = (backend_root / "outputs" / tender_id / "submission_docs").resolve()
    # Prevent path traversal
    file_path = (base / doc_name).resolve()
    if not str(file_path).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Document {doc_name} not found for tender {tender_id}")
    return FileResponse(str(file_path), filename=file_path.name)
