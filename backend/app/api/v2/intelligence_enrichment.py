"""
Intelligence Enrichment API
Endpoints for enriching knowledge platform with calculated metrics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.intelligence_enrichment_service import IntelligenceEnrichmentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["intelligence"])


@router.post("/enrich")
async def enrich_intelligence(
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Trigger comprehensive intelligence enrichment.
    Calculates and populates all missing metrics:
    - Contractor performance (win_rate, completion_rate, on_time_rate, delay_days)
    - Agency statistics (contracts, amounts, trends)
    - Zone statistics and patterns
    - Discount patterns by agency/zone/method
    - Award intelligence by quarter/year
    - Health scores and rankings
    """
    try:
        service = IntelligenceEnrichmentService(db)
        results = await service.enrich_all_intelligence()
        return {
            "status": "success",
            "message": "Intelligence enrichment complete",
            "results": results,
        }
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_enrichment_summary(
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Get summary of enriched intelligence data."""
    try:
        service = IntelligenceEnrichmentService(db)
        summary = await service.get_enrichment_summary()
        return {
            "status": "success",
            "data": summary,
        }
    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contractors/top")
async def get_top_contractors(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Get top contractors by health score and performance."""
    try:
        contractors = await db.execute(text("""
            SELECT
                contractor_id,
                c.contractor_name,
                d.total_contracts,
                d.total_amount_bdt,
                d.win_rate,
                d.completion_rate,
                d.on_time_rate,
                d.health_score,
                d.agencies_worked,
                d.districts_worked
            FROM contractor_dna d
            JOIN contractors c ON c.id = d.contractor_id
            WHERE d.health_score > 0 AND d.total_contracts > 0
            ORDER BY d.health_score DESC, d.total_amount_bdt DESC
            LIMIT :limit
        """), {"limit": limit})

        results = []
        for row in contractors:
            results.append({
                "contractor_id": row[0],
                "contractor_name": row[1],
                "total_contracts": row[2],
                "total_amount_bdt": row[3],
                "win_rate": round(row[4], 2) if row[4] else 0,
                "completion_rate": round(row[5], 2) if row[5] else 0,
                "on_time_rate": round(row[6], 2) if row[6] else 0,
                "health_score": round(row[7], 3) if row[7] else 0,
                "agencies_worked": row[8] or 0,
                "districts_worked": row[9] or 0,
            })

        return {
            "status": "success",
            "count": len(results),
            "data": results,
        }
    except Exception as e:
        logger.error(f"Failed to get top contractors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agencies/statistics")
async def get_agency_statistics(
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Get agency-level intelligence statistics."""
    try:
        agencies = await db.execute(text("""
            SELECT
                agency_code,
                total_contracts,
                total_amount_bdt,
                ROUND(avg_npp::numeric, 4) AS avg_npp,
                npp_trend,
                preferred_method
            FROM agency_intelligence
            WHERE total_contracts > 0
            ORDER BY total_contracts DESC
        """))

        results = []
        for row in agencies:
            results.append({
                "agency_code": row[0],
                "total_contracts": row[1],
                "total_amount_bdt": row[2],
                "avg_npp": row[3],
                "npp_trend": row[4],
                "preferred_method": row[5],
            })

        return {
            "status": "success",
            "count": len(results),
            "data": results,
        }
    except Exception as e:
        logger.error(f"Failed to get agency statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zones/statistics")
async def get_zone_statistics(
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Get zone-level intelligence statistics."""
    try:
        zones = await db.execute(text("""
            SELECT
                zone_name,
                total_contracts,
                total_amount_bdt,
                active_agencies,
                ROUND(avg_npp::numeric, 4) AS avg_npp
            FROM zone_intelligence
            WHERE total_contracts > 0
            ORDER BY total_contracts DESC
        """))

        results = []
        for row in zones:
            results.append({
                "zone_name": row[0],
                "total_contracts": row[1],
                "total_amount_bdt": row[2],
                "active_agencies": row[3],
                "avg_npp": row[4],
            })

        return {
            "status": "success",
            "count": len(results),
            "data": results,
        }
    except Exception as e:
        logger.error(f"Failed to get zone statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/discount")
async def get_discount_patterns(
    agency_code: str = Query(None),
    zone_name: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Get discount patterns with optional filtering."""
    try:
        query = """
            SELECT
                agency_code,
                zone_name,
                procurement_method,
                sample_size,
                ROUND(avg_npp::numeric, 4) AS avg_npp,
                ROUND(min_npp::numeric, 4) AS min_npp,
                ROUND(max_npp::numeric, 4) AS max_npp,
                ROUND(median_npp::numeric, 4) AS median_npp,
                ROUND(stddev_npp::numeric, 4) AS stddev_npp
            FROM discount_patterns
            WHERE 1=1
        """
        params = {}

        if agency_code:
            query += " AND agency_code = :agency_code"
            params["agency_code"] = agency_code

        if zone_name:
            query += " AND zone_name = :zone_name"
            params["zone_name"] = zone_name

        query += " ORDER BY sample_size DESC LIMIT :limit"
        params["limit"] = limit

        patterns = await db.execute(text(query), params)

        results = []
        for row in patterns:
            results.append({
                "agency_code": row[0],
                "zone_name": row[1],
                "procurement_method": row[2],
                "sample_size": row[3],
                "avg_npp": row[4],
                "min_npp": row[5],
                "max_npp": row[6],
                "median_npp": row[7],
                "stddev_npp": row[8],
            })

        return {
            "status": "success",
            "count": len(results),
            "filters": {"agency_code": agency_code, "zone_name": zone_name},
            "data": results,
        }
    except Exception as e:
        logger.error(f"Failed to get discount patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contractor/{contractor_name}")
async def get_contractor_intelligence(
    contractor_name: str,
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Get detailed intelligence for a specific contractor."""
    try:
        result = await db.execute(text("""
            SELECT
                d.contractor_id,
                c.contractor_name,
                d.total_contracts,
                d.total_amount_bdt,
                d.avg_award_bdt,
                d.win_rate,
                d.avg_discount_pct,
                d.completion_rate,
                d.on_time_rate,
                d.avg_delay_days,
                d.agencies_worked,
                d.districts_worked,
                d.avg_npp,
                d.npp_volatility,
                d.health_score,
                d.first_award_date,
                d.last_award_date,
                d.preferred_agency,
                d.preferred_zone
            FROM contractor_dna d
            JOIN contractors c ON c.id = d.contractor_id
            WHERE LOWER(c.contractor_name) LIKE LOWER(:name)
            LIMIT 1
        """), {"name": f"%{contractor_name}%"})

        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Contractor not found")

        return {
            "status": "success",
            "data": {
                "contractor_id": row[0],
                "contractor_name": row[1],
                "total_contracts": row[2],
                "total_amount_bdt": row[3],
                "avg_award_bdt": row[4],
                "win_rate": round(row[5], 2) if row[5] else 0,
                "avg_discount_pct": round(row[6], 2) if row[6] else 0,
                "completion_rate": round(row[7], 2) if row[7] else 0,
                "on_time_rate": round(row[8], 2) if row[8] else 0,
                "avg_delay_days": round(row[9], 1) if row[9] else 0,
                "agencies_worked": row[10],
                "districts_worked": row[11],
                "avg_npp": round(row[12], 4) if row[12] else 0,
                "npp_volatility": round(row[13], 4) if row[13] else 0,
                "health_score": round(row[14], 3) if row[14] else 0,
                "first_award_date": row[15],
                "last_award_date": row[16],
                "preferred_agency": row[17],
                "preferred_zone": row[18],
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contractor intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))
