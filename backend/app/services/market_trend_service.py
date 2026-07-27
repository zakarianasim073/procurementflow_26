"""Market Trend Analysis Service (T-024): Time series forecasting, seasonal decomposition, anomaly detection."""

from __future__ import annotations

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal

from sqlalchemy import select, text, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MarketTrendService:
    """Time series analysis of market trends for procurement categories."""

    @staticmethod
    async def get_trend_data(
        db: AsyncSession,
        zone_id: str,
        category_id: str,
        lookback_days: int = 365,
        period_type: str = "day",
    ) -> List[Dict[str, Any]]:
        """Fetch historical price data for trend analysis.

        Args:
            zone_id: Procurement zone
            category_id: Procurement category
            lookback_days: How many days of history to fetch
            period_type: Aggregation granularity (day, week, month)

        Returns:
            List of {period_date, avg_price, tender_count, bid_count, ...}
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        # Aggregate tender data into periods
        if period_type == "day":
            period_format = "DATE(ft.published_date)"
        elif period_type == "week":
            period_format = "DATE_TRUNC('week', ft.published_date)"
        elif period_type == "month":
            period_format = "DATE_TRUNC('month', ft.published_date)"
        else:
            period_format = "DATE(ft.published_date)"

        result = await db.execute(
            text(f"""
                SELECT
                    {period_format} as period_date,
                    AVG(ft.tender_value_bdt) as avg_price,
                    MIN(ft.tender_value_bdt) as min_price,
                    MAX(ft.tender_value_bdt) as max_price,
                    STDDEV(ft.tender_value_bdt) as std_price,
                    COUNT(DISTINCT ft.tender_id) as tender_count,
                    COALESCE(SUM(ft.bid_count), 0) as bid_count,
                    COALESCE(AVG(ft.bid_count), 0) as avg_bid_count
                FROM fact_tenders ft
                WHERE ft.zone_id = :zone_id
                    AND ft.category_id = :category_id
                    AND ft.published_date >= :cutoff
                    AND ft.tender_value_bdt > 0
                GROUP BY {period_format}
                ORDER BY period_date ASC
            """),
            {
                "zone_id": zone_id,
                "category_id": category_id,
                "cutoff": cutoff,
            }
        )

        data = []
        for row in result.fetchall():
            data.append({
                "period_date": row[0],
                "avg_price": float(row[1] or 0),
                "min_price": float(row[2] or 0),
                "max_price": float(row[3] or 0),
                "std_price": float(row[4] or 0),
                "tender_count": row[5],
                "bid_count": row[6],
                "avg_bid_count": float(row[7] or 0),
            })

        logger.info(f"Fetched {len(data)} periods for trend analysis ({zone_id}/{category_id})")
        return data

    @staticmethod
    async def decompose_trend(
        db: AsyncSession,
        zone_id: str,
        category_id: str,
        lookback_days: int = 730,
    ) -> Dict[str, Any]:
        """Decompose trend into trend, seasonal, and residual components.

        Uses additive decomposition (STL or manual if statsmodels unavailable).

        Returns:
            {trend_component, seasonal_component, residual_component, seasonal_strength, variance_explained}
        """
        try:
            from statsmodels.tsa.seasonal import seasonal_decompose
            import numpy as np
        except ImportError:
            logger.warning("statsmodels not installed; using simplified decomposition")
            return await MarketTrendService._simplified_decompose(db, zone_id, category_id, lookback_days)

        data = await MarketTrendService.get_trend_data(
            db, zone_id, category_id, lookback_days, period_type="day"
        )

        if len(data) < 60:
            return {
                "error": f"Insufficient data: {len(data)} days, need ≥60 for decomposition"
            }

        # Extract price time series
        prices = np.array([d["avg_price"] for d in data])

        # Decompose with annual seasonality (365 days)
        period = min(365, len(prices) // 2)
        decomposition = seasonal_decompose(prices, model="additive", period=period)

        # Convert to JSON-serializable format
        trend_component = decomposition.trend.tolist()
        seasonal_component = decomposition.seasonal[:period].tolist()
        residual_component = decomposition.resid.tolist()

        # Calculate seasonal strength (variance of seasonal / total variance)
        seasonal_var = np.var(decomposition.seasonal)
        total_var = np.var(prices)
        seasonal_strength = float(seasonal_var / (total_var or 1))

        # Calculate reconstruction error (R²)
        reconstructed = (decomposition.trend + decomposition.seasonal + decomposition.resid)
        mae = float(np.mean(np.abs(prices - reconstructed)))

        # Find peak season months (highest seasonal effect)
        monthly_seasonal = {}
        for i, date_obj in enumerate([d["period_date"] for d in data]):
            if hasattr(date_obj, "month"):
                month = date_obj.month
            else:
                month = int(str(date_obj)[:7].split("-")[1])
            if month not in monthly_seasonal:
                monthly_seasonal[month] = []
            if i < len(decomposition.seasonal):
                monthly_seasonal[month].append(decomposition.seasonal[i])

        peak_months = sorted(
            monthly_seasonal.keys(),
            key=lambda m: sum(monthly_seasonal[m]) / len(monthly_seasonal[m]),
            reverse=True,
        )[:3]

        logger.info(
            f"Decomposed {zone_id}/{category_id}: "
            f"seasonal_strength={seasonal_strength:.2%}, mae={mae:.2f}, "
            f"peak_months={peak_months}"
        )

        return {
            "trend_component": trend_component,
            "seasonal_component": seasonal_component,
            "residual_component": residual_component,
            "seasonal_strength": seasonal_strength,
            "peak_season_months": ",".join(str(m) for m in peak_months),
            "variance_explained": 1.0 - (np.var(residual_component) / (total_var or 1)),
            "mae": mae,
            "data_points_used": len(prices),
        }

    @staticmethod
    async def _simplified_decompose(
        db: AsyncSession,
        zone_id: str,
        category_id: str,
        lookback_days: int = 730,
    ) -> Dict[str, Any]:
        """Simplified trend decomposition without statsmodels."""
        data = await MarketTrendService.get_trend_data(
            db, zone_id, category_id, lookback_days, period_type="day"
        )

        if len(data) < 60:
            return {"error": f"Insufficient data: {len(data)} days"}

        prices = [d["avg_price"] for d in data]

        # Simple trend: moving average
        window = 30
        trend = []
        for i in range(len(prices)):
            start = max(0, i - window // 2)
            end = min(len(prices), i + window // 2 + 1)
            trend.append(sum(prices[start:end]) / len(prices[start:end]))

        # Seasonal: detrended component, averaged by day-of-year
        seasonal_by_doy = {}
        for i, d in enumerate(data):
            if hasattr(d["period_date"], "timetuple"):
                doy = d["period_date"].timetuple().tm_yday
            else:
                doy = int(d["period_date"].strftime("%j"))
            detrended = prices[i] - trend[i]
            if doy not in seasonal_by_doy:
                seasonal_by_doy[doy] = []
            seasonal_by_doy[doy].append(detrended)

        seasonal_pattern = {}
        for doy, values in seasonal_by_doy.items():
            seasonal_pattern[doy] = sum(values) / len(values)

        # Residual
        seasonal = [seasonal_pattern.get(int(d["period_date"].strftime("%j")), 0) for d in data]
        residual = [prices[i] - trend[i] - seasonal[i] for i in range(len(prices))]

        # Metrics
        seasonal_var = sum((s - sum(seasonal) / len(seasonal)) ** 2 for s in seasonal) / len(seasonal)
        total_var = sum((p - sum(prices) / len(prices)) ** 2 for p in prices) / len(prices)
        seasonal_strength = seasonal_var / (total_var or 1)

        mae = sum(abs(r) for r in residual) / len(residual)

        peak_doys = sorted(seasonal_pattern.keys(), key=lambda doy: seasonal_pattern[doy], reverse=True)[:3]
        peak_months = set()
        for doy in peak_doys:
            import datetime as dt
            month = dt.datetime.strptime(str(doy), "%j").month
            peak_months.add(month)

        return {
            "trend_component": trend,
            "seasonal_component": [seasonal_pattern.get(d, 0) for d in range(1, 366)][:365],
            "residual_component": residual,
            "seasonal_strength": seasonal_strength,
            "peak_season_months": ",".join(str(m) for m in sorted(peak_months)),
            "variance_explained": 1.0 - (sum(r ** 2 for r in residual) / sum((p - sum(prices) / len(prices)) ** 2 for p in prices)),
            "mae": mae,
            "data_points_used": len(prices),
        }

    @staticmethod
    async def detect_anomalies(
        db: AsyncSession,
        zone_id: str,
        category_id: str,
        lookback_days: int = 90,
        sensitivity: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Detect price anomalies using statistical methods.

        Sensitivity: low (2.5σ), medium (2σ), high (1.5σ)

        Returns:
            List of {period_date, anomaly_type, deviation_pct, severity, message}
        """
        sensitivity_thresholds = {
            "low": 2.5,
            "medium": 2.0,
            "high": 1.5,
        }
        threshold = sensitivity_thresholds.get(sensitivity, 2.0)

        data = await MarketTrendService.get_trend_data(
            db, zone_id, category_id, lookback_days, period_type="day"
        )

        if len(data) < 30:
            return []

        prices = [d["avg_price"] for d in data]

        # Calculate rolling statistics
        window = 14  # 2-week window
        anomalies = []

        for i in range(window, len(prices)):
            window_prices = prices[max(0, i - window) : i]
            mean = sum(window_prices) / len(window_prices)
            variance = sum((p - mean) ** 2 for p in window_prices) / len(window_prices)
            std = variance ** 0.5

            current_price = prices[i]
            z_score = (current_price - mean) / (std or 1)

            if abs(z_score) > threshold:
                deviation_pct = ((current_price - mean) / (mean or 1)) * 100

                # Classify anomaly
                if z_score > threshold:
                    anomaly_type = "spike"
                    severity = "high" if z_score > 3 else "medium" if z_score > 2.5 else "low"
                else:
                    anomaly_type = "drop"
                    severity = "high" if z_score < -3 else "medium" if z_score < -2.5 else "low"

                anomalies.append({
                    "period_date": data[i]["period_date"],
                    "observed_price": current_price,
                    "expected_price": mean,
                    "anomaly_type": anomaly_type,
                    "deviation_pct": deviation_pct,
                    "severity": severity,
                    "confidence": min(0.99, (abs(z_score) / threshold) * 0.95),
                    "z_score": z_score,
                    "message": f"{anomaly_type.capitalize()} detected: {current_price:.0f} BDT vs expected {mean:.0f} BDT ({deviation_pct:+.1f}%)",
                })

        logger.info(f"Detected {len(anomalies)} anomalies in {zone_id}/{category_id}")
        return anomalies

    @staticmethod
    async def forecast_trend(
        db: AsyncSession,
        zone_id: str,
        category_id: str,
        forecast_days: int = 30,
    ) -> Dict[str, Any]:
        """Forecast future price trends using exponential smoothing.

        Returns:
            {forecast_dates, forecast_prices, confidence_intervals_low, confidence_intervals_high}
        """
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            import numpy as np
        except ImportError:
            logger.warning("statsmodels not installed; using simplified forecast")
            return await MarketTrendService._simplified_forecast(db, zone_id, category_id, forecast_days)

        data = await MarketTrendService.get_trend_data(
            db, zone_id, category_id, lookback_days=180, period_type="day"
        )

        if len(data) < 30:
            return {"error": "Insufficient data for forecasting"}

        prices = np.array([d["avg_price"] for d in data])

        # Fit exponential smoothing model
        try:
            model = ExponentialSmoothing(prices, trend="add", seasonal=None, seasonal_periods=None)
            fitted = model.fit()
            forecast = fitted.forecast(steps=forecast_days)
        except Exception as e:
            logger.warning(f"ExponentialSmoothing failed: {e}; using simple exponential smoothing")
            alpha = 0.3
            forecast = []
            last = prices[-1]
            for _ in range(forecast_days):
                last = alpha * prices[-1] + (1 - alpha) * last
                forecast.append(last)
            forecast = np.array(forecast)

        # Generate forecast dates
        last_date = data[-1]["period_date"]
        forecast_dates = [
            (last_date + timedelta(days=i + 1)).isoformat()
            for i in range(forecast_days)
        ]

        # Confidence intervals (15% band)
        std_error = float(np.std(prices))
        confidence_low = (forecast * 0.85).tolist()
        confidence_high = (forecast * 1.15).tolist()

        return {
            "forecast_dates": forecast_dates,
            "forecast_prices": forecast.tolist(),
            "confidence_low": confidence_low,
            "confidence_high": confidence_high,
            "forecast_days": forecast_days,
        }

    @staticmethod
    async def _simplified_forecast(
        db: AsyncSession,
        zone_id: str,
        category_id: str,
        forecast_days: int = 30,
    ) -> Dict[str, Any]:
        """Simple exponential smoothing forecast without statsmodels."""
        data = await MarketTrendService.get_trend_data(
            db, zone_id, category_id, lookback_days=180, period_type="day"
        )

        if len(data) < 30:
            return {"error": "Insufficient data for forecasting"}

        prices = [d["avg_price"] for d in data]

        # Simple exponential smoothing
        alpha = 0.2
        forecast = []
        level = prices[-1]
        for _ in range(forecast_days):
            forecast.append(level)
            level = alpha * prices[-1] + (1 - alpha) * level

        # Generate dates
        last_date = data[-1]["period_date"]
        forecast_dates = [
            (last_date + timedelta(days=i + 1)).isoformat()
            for i in range(forecast_days)
        ]

        # Std error from recent prices
        recent_std = (sum((p - sum(prices[-30:]) / 30) ** 2 for p in prices[-30:]) / 30) ** 0.5

        return {
            "forecast_dates": forecast_dates,
            "forecast_prices": forecast,
            "confidence_low": [p * 0.85 for p in forecast],
            "confidence_high": [p * 1.15 for p in forecast],
            "forecast_days": forecast_days,
        }
