"""Market Trend Analysis API endpoints (T-024: Time Series Analysis)."""

from __future__ import annotations

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.db.base import get_async_session
from app.services.market_trend_service import MarketTrendService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market-trends", tags=["market-trends"])


# ── Request Models ──────────────────────────────────────────────────


class TrendDataPoint(BaseModel):
    """Single time series data point."""

    period_date: str = Field(..., description="Period start date (ISO format)")
    avg_price: float = Field(..., description="Average tender price (BDT)")
    min_price: float = Field(..., description="Minimum tender price")
    max_price: float = Field(..., description="Maximum tender price")
    std_price: float = Field(..., description="Price standard deviation")
    tender_count: int = Field(..., description="Number of tenders")
    bid_count: int = Field(..., description="Total bids")
    avg_bid_count: float = Field(..., description="Average bids per tender")


class TrendDecompositionResponse(BaseModel):
    """Seasonal decomposition of trend."""

    zone_id: str
    category_id: str
    seasonal_strength: float = Field(..., ge=0, le=1, description="Strength of seasonality")
    peak_season_months: str = Field(..., description="Comma-separated peak months")
    variance_explained: float = Field(..., ge=0, le=1)
    data_points_used: int
    mae: float = Field(..., description="Mean absolute error of reconstruction")


class Anomaly(BaseModel):
    """Detected price anomaly."""

    period_date: str
    anomaly_type: str = Field(..., description="spike or drop")
    observed_price: float
    expected_price: float
    deviation_pct: float
    severity: str = Field(..., description="low, medium, high, critical")
    confidence: float = Field(..., ge=0, le=1)
    message: str


class PriceForecast(BaseModel):
    """Price forecast for future periods."""

    forecast_dates: List[str]
    forecast_prices: List[float]
    confidence_low: List[float]
    confidence_high: List[float]
    forecast_days: int


class TrendSummary(BaseModel):
    """Complete market trend summary."""

    zone_id: str
    category_id: str
    current_price: float
    price_change_pct: float = Field(..., description="% change vs previous period")
    trend_direction: str = Field(..., description="increasing, stable, decreasing")
    seasonal_strength: float
    peak_season_months: str
    recent_anomalies: int = Field(..., description="Anomalies in last 30 days")
    forecast_30d: List[float] = Field(..., description="30-day price forecast")
    forecast_confidence: float


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/{zone_id}/{category_id}/trends", response_model=List[TrendDataPoint])
async def get_trend_data(
    zone_id: str = Path(..., description="Procurement zone (A, B, C, D)"),
    category_id: str = Path(..., description="Procurement category ID"),
    lookback_days: int = Query(90, ge=7, le=730, description="Days of history to fetch"),
    period_type: str = Query("day", pattern="^(day|week|month)$"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[dict]:
    """Get historical price trend data.

    Time series data aggregated by period (day/week/month) showing price movements
    and market activity for a specific zone/category combination.

    **Outputs**:
    - Average, min, max prices (BDT)
    - Price volatility (standard deviation)
    - Market participation (tender count, bid counts)

    **Use case**: Visualize market trends, identify seasonal patterns
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    data = await MarketTrendService.get_trend_data(
        db,
        zone_id=zone_id,
        category_id=category_id,
        lookback_days=lookback_days,
        period_type=period_type,
    )

    return data


@router.get("/{zone_id}/{category_id}/decomposition", response_model=TrendDecompositionResponse)
async def get_trend_decomposition(
    zone_id: str = Path(...),
    category_id: str = Path(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get seasonal decomposition of price trends.

    Decomposes historical prices into three components:
    1. **Trend**: Long-term direction
    2. **Seasonal**: Recurring patterns (monthly, seasonal)
    3. **Residual**: Random noise and anomalies

    **Outputs**:
    - Seasonal strength (0-1): how pronounced is seasonality?
    - Peak months: when do prices typically spike?
    - Variance explained: quality of decomposition

    **Use case**: Understand market seasonality, forecast timing
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    decomp = await MarketTrendService.decompose_trend(
        db,
        zone_id=zone_id,
        category_id=category_id,
        lookback_days=730,
    )

    if "error" in decomp:
        raise HTTPException(status_code=503, detail=decomp["error"])

    return {
        "zone_id": zone_id,
        "category_id": category_id,
        **decomp,
    }


@router.get("/{zone_id}/{category_id}/anomalies", response_model=List[Anomaly])
async def get_anomalies(
    zone_id: str = Path(...),
    category_id: str = Path(...),
    lookback_days: int = Query(90, ge=7, le=365),
    sensitivity: str = Query("medium", pattern="^(low|medium|high)$"),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[dict]:
    """Detect price anomalies in trend data.

    Identifies statistical outliers that deviate significantly from expected behavior.
    Uses rolling z-score analysis.

    **Sensitivity levels**:
    - low: 2.5σ threshold (conservative, fewer false positives)
    - medium: 2σ threshold (balanced)
    - high: 1.5σ threshold (aggressive, more sensitivity)

    **Outputs**:
    - Anomaly type: spike or drop
    - Deviation: % difference from expected
    - Severity: low to critical
    - Confidence: 0-1 confidence in detection

    **Use case**: Alert on price shocks, investigate market disruptions
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    anomalies = await MarketTrendService.detect_anomalies(
        db,
        zone_id=zone_id,
        category_id=category_id,
        lookback_days=lookback_days,
        sensitivity=sensitivity,
    )

    return anomalies[:limit]


@router.get("/{zone_id}/{category_id}/forecast", response_model=PriceForecast)
async def get_price_forecast(
    zone_id: str = Path(...),
    category_id: str = Path(...),
    forecast_days: int = Query(30, ge=7, le=90),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Forecast future price trends.

    Uses exponential smoothing to project price movements for the next N days.
    Includes confidence intervals (±15% by default).

    **Outputs**:
    - Forecast dates (ISO format)
    - Predicted prices (BDT)
    - Confidence bands (low/high)

    **Accuracy**: ±15% confidence interval (based on recent volatility)

    **Use case**: Budget planning, tender price validation
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    forecast = await MarketTrendService.forecast_trend(
        db,
        zone_id=zone_id,
        category_id=category_id,
        forecast_days=forecast_days,
    )

    if "error" in forecast:
        raise HTTPException(status_code=503, detail=forecast["error"])

    return forecast


@router.get("/{zone_id}/{category_id}/summary", response_model=TrendSummary)
async def get_trend_summary(
    zone_id: str = Path(...),
    category_id: str = Path(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get complete market trend summary.

    Combined view of current prices, trends, seasonality, anomalies, and forecasts.
    Single endpoint for dashboard consumption.

    **Outputs**:
    - Current price and recent change
    - Trend direction (increasing/stable/decreasing)
    - Seasonal patterns
    - Recent anomalies
    - 30-day price forecast

    **Use case**: Dashboard, market intelligence reports
    """
    if not user or not user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Authentication required")

    # Fetch all components
    trends = await MarketTrendService.get_trend_data(db, zone_id, category_id, lookback_days=90)
    decomp = await MarketTrendService.decompose_trend(db, zone_id, category_id)
    anomalies = await MarketTrendService.detect_anomalies(db, zone_id, category_id, lookback_days=30)
    forecast = await MarketTrendService.forecast_trend(db, zone_id, category_id, forecast_days=30)

    if not trends or "error" in decomp or "error" in forecast:
        raise HTTPException(status_code=503, detail="Insufficient data for summary")

    # Extract current price and trend
    current_price = trends[-1]["avg_price"] if trends else 0
    prev_price = trends[-8]["avg_price"] if len(trends) > 7 else current_price
    price_change = ((current_price - prev_price) / (prev_price or 1)) * 100

    # Determine trend direction
    if price_change > 2:
        trend_direction = "increasing"
    elif price_change < -2:
        trend_direction = "decreasing"
    else:
        trend_direction = "stable"

    # Extract forecast
    forecast_30d = forecast.get("forecast_prices", [])[:30] if "forecast_prices" in forecast else []
    forecast_prices = forecast.get("forecast_prices", [])
    forecast_confidence = min(0.95, 0.7 + (decomp.get("seasonal_strength", 0) * 0.2))

    return {
        "zone_id": zone_id,
        "category_id": category_id,
        "current_price": current_price,
        "price_change_pct": price_change,
        "trend_direction": trend_direction,
        "seasonal_strength": decomp.get("seasonal_strength", 0),
        "peak_season_months": decomp.get("peak_season_months", ""),
        "recent_anomalies": len(anomalies),
        "forecast_30d": forecast_30d,
        "forecast_confidence": min(0.95, 0.7 + (decomp.get("seasonal_strength", 0) * 0.2)),
    }
