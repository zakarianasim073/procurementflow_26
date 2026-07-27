"""ML Service (T-023): Price prediction models for tenders and bids."""

from __future__ import annotations

import logging
import hashlib
import json
import pickle
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MLService:
    """Machine learning model training, inference, and caching."""

    # Feature engineering for tender price prediction
    TENDER_FEATURES = [
        "zone_id",                 # Categorical
        "agency_id",               # Categorical
        "category_id",             # Categorical
        "historical_avg_price",    # Continuous - avg price for category/zone
        "historical_std_price",    # Continuous - price volatility
        "tender_duration_days",    # Continuous - time from publish to deadline
        "seasonality_month",       # Categorical - month number
        "market_trend_3m",         # Continuous - 3-month price trend
        "market_trend_12m",        # Continuous - 12-month price trend
    ]

    # Features for winning bid prediction
    BID_FEATURES = [
        "zone_id",
        "agency_id",
        "category_id",
        "tender_estimated_value",  # Continuous
        "historical_bid_ratio",     # Continuous - avg winning bid / estimated value
        "contractor_avg_bid_ratio", # Continuous - contractor's average bid pattern
        "market_avg_bid",           # Continuous - market average bid
        "bid_competition_count",    # Continuous - number of bidders
        "contractor_category_exp",  # Continuous - contractor's experience in category
    ]

    @staticmethod
    async def get_training_data(
        db: AsyncSession, lookback_months: int = 24
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """Fetch historical tender data for model training.

        Args:
            lookback_months: How many months of historical data to use

        Returns:
            Tuple of (features_list, target_prices_list)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_months * 30)

        result = await db.execute(
            text("""
                SELECT
                    ft.tender_id,
                    ft.zone_id,
                    ft.agency_id,
                    ft.category_id,
                    ft.tender_value_bdt,
                    ft.bid_count,
                    EXTRACT(DAY FROM (ft.deadline_date - ft.published_date)) as duration_days,
                    EXTRACT(MONTH FROM ft.published_date) as publish_month,
                    COALESCE(
                        (SELECT AVG(tender_value_bdt) FROM fact_tenders ft2
                         WHERE ft2.category_id = ft.category_id
                         AND ft2.zone_id = ft.zone_id
                         AND ft2.published_date > :cutoff),
                        ft.tender_value_bdt
                    ) as category_zone_avg,
                    COALESCE(
                        (SELECT STDDEV(tender_value_bdt) FROM fact_tenders ft2
                         WHERE ft2.category_id = ft.category_id
                         AND ft2.zone_id = ft.zone_id
                         AND ft2.published_date > :cutoff),
                        0
                    ) as category_zone_std
                FROM fact_tenders ft
                WHERE ft.published_date >= :cutoff
                    AND ft.tender_value_bdt > 0
                ORDER BY ft.published_date DESC
                LIMIT 1000
            """,
                {"cutoff": cutoff},
            )
        )

        features = []
        targets = []

        for row in result.fetchall():
            feature_dict = {
                "zone_id": row[1],
                "agency_id": row[2],
                "category_id": row[3],
                "historical_avg_price": float(row[8] or row[4]),
                "historical_std_price": float(row[9] or 0),
                "tender_duration_days": int(row[6] or 0),
                "seasonality_month": int(row[7] or 1),
                "market_trend_3m": 1.0,  # Would calculate from moving average
                "market_trend_12m": 1.0,  # Would calculate from moving average
            }
            features.append(feature_dict)
            targets.append(float(row[4] or 0))

        logger.info(f"Fetched {len(features)} tender records for training")
        return features, targets

    @staticmethod
    async def train_tender_price_model(db: AsyncSession) -> Dict[str, Any]:
        """Train tender price prediction model (XGBoost).

        Returns:
            Model metadata (RMSE, R², sample count, model_id)
        """
        try:
            import xgboost as xgb
            from sklearn.preprocessing import LabelEncoder
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_squared_error, r2_score
        except ImportError:
            logger.error("XGBoost or scikit-learn not installed")
            return {"error": "ML dependencies missing"}

        features, targets = await MLService.get_training_data(db, lookback_months=24)

        if len(features) < 100:
            return {"error": f"Insufficient data: {len(features)} samples, need ≥100"}

        # Feature engineering: fit each categorical encoder on the FULL column
        # (per-row fit_transform would map every value to 0).
        cat_feats = ["zone_id", "agency_id", "category_id"]
        encoders = {
            f: LabelEncoder().fit([str(fd.get(f, "unknown")) for fd in features])
            for f in cat_feats
        }
        X_processed = []
        for feat_dict in features:
            row = []
            for feat_name in MLService.TENDER_FEATURES:
                if feat_name in cat_feats:
                    row.append(int(encoders[feat_name].transform([str(feat_dict.get(feat_name, "unknown"))])[0]))
                else:
                    row.append(float(feat_dict.get(feat_name, 0)))
            X_processed.append(row)

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X_processed, targets, test_size=0.2, random_state=42
        )

        # Train XGBoost model
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

        # Evaluate
        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)

        train_rmse = float(mean_squared_error(y_train, y_pred_train) ** 0.5)
        val_rmse = float(mean_squared_error(y_val, y_pred_val) ** 0.5)
        train_r2 = float(r2_score(y_train, y_pred_train))
        val_r2 = float(r2_score(y_val, y_pred_val))

        # Serialize model
        model_blob = pickle.dumps(model)

        # Feature importance
        feature_importance = dict(
            zip(MLService.TENDER_FEATURES, model.feature_importances_.tolist())
        )

        logger.info(
            f"Trained tender price model: RMSE={val_rmse:.2f}, R²={val_r2:.3f}, "
            f"samples={len(X_train)}, importance={feature_importance}"
        )

        return {
            "model_type": "xgboost",
            "training_rmse": train_rmse,
            "training_r2": train_r2,
            "validation_rmse": val_rmse,
            "validation_r2": val_r2,
            "training_samples": len(X_train),
            "feature_count": len(MLService.TENDER_FEATURES),
            "feature_importance": feature_importance,
            "model_blob": model_blob,
            "mean_target": float(sum(y_train) / len(y_train)),
        }

    @staticmethod
    async def predict_tender_price(
        db: AsyncSession,
        zone_id: str,
        agency_id: str,
        category_id: str,
        duration_days: int,
        month: int = None,
    ) -> Dict[str, Any]:
        """Predict tender price for given parameters.

        Args:
            zone_id: Procurement zone
            agency_id: Procuring agency
            category_id: Procurement category
            duration_days: Days from publish to deadline
            month: Month of publication (1-12)

        Returns:
            Predicted price, confidence interval, confidence score
        """
        # Try to load active model
        result = await db.execute(
            text(
                "SELECT model_blob, feature_importance_json "
                "FROM tender_price_models "
                "WHERE is_active = true ORDER BY deployed_at DESC LIMIT 1"
            )
        )
        model_row = result.first()

        if not model_row:
            return {"error": "No active model available"}

        model_blob, feature_importance_json = model_row

        try:
            model = pickle.loads(model_blob)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return {"error": "Model deserialization failed"}

        # Prepare features
        if month is None:
            month = datetime.now().month

        # Get historical data for category/zone
        hist_result = await db.execute(
            text("""
                SELECT
                    AVG(tender_value_bdt) as avg_price,
                    STDDEV(tender_value_bdt) as std_price
                FROM fact_tenders
                WHERE category_id = :category_id
                    AND zone_id = :zone_id
                    AND tender_value_bdt > 0
                    AND published_date > NOW() - INTERVAL '2 years'
            """,
                {"category_id": category_id, "zone_id": zone_id},
            )
        )
        hist_row = hist_result.first()
        avg_price = float(hist_row[0] or 0) if hist_row else 0
        std_price = float(hist_row[1] or 0) if hist_row else 0

        # Build feature vector
        features = [
            zone_id,
            agency_id,
            category_id,
            avg_price,
            std_price,
            float(duration_days),
            float(month),
            1.0,  # market_trend_3m
            1.0,  # market_trend_12m
        ]

        try:
            predicted = model.predict([features])[0]
            # Confidence interval: ±20% (can be refined with quantile regression)
            confidence = min(0.95, avg_price / (std_price or 1))

            return {
                "predicted_price": float(predicted),
                "predicted_low": float(predicted * 0.80),
                "predicted_high": float(predicted * 1.20),
                "confidence_score": min(1.0, max(0.0, confidence)),
                "mean_historical": avg_price,
            }
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {"error": str(e)}

    @staticmethod
    async def calculate_prediction_error(
        predicted: float, actual: float
    ) -> Tuple[float, float]:
        """Calculate RMSE and MAPE for a single prediction.

        Returns:
            (rmse, mape_pct)
        """
        error = abs(actual - predicted)
        rmse = error
        mape = (error / actual * 100) if actual != 0 else 0
        return rmse, mape

    @staticmethod
    async def get_model_status(db: AsyncSession) -> Dict[str, Any]:
        """Get status of currently active ML models.

        Returns:
            Model versions, performance metrics, last training date
        """
        tender_result = await db.execute(
            text("""
                SELECT
                    model_version,
                    validation_rmse,
                    validation_r2,
                    training_samples,
                    trained_at,
                    deployed_at
                FROM tender_price_models
                WHERE is_active = true
                ORDER BY deployed_at DESC
                LIMIT 1
            """)
        )
        tender_row = tender_result.first()

        bid_result = await db.execute(
            text("""
                SELECT
                    model_version,
                    validation_rmse,
                    validation_r2,
                    training_samples,
                    trained_at,
                    deployed_at
                FROM bid_price_models
                WHERE is_active = true
                ORDER BY deployed_at DESC
                LIMIT 1
            """)
        )
        bid_row = bid_result.first()

        return {
            "tender_price_model": {
                "version": tender_row[0] if tender_row else None,
                "validation_rmse": float(tender_row[1]) if tender_row and tender_row[1] else None,
                "validation_r2": float(tender_row[2]) if tender_row and tender_row[2] else None,
                "training_samples": tender_row[3] if tender_row else 0,
                "trained_at": str(tender_row[4]) if tender_row and tender_row[4] else None,
                "deployed_at": str(tender_row[5]) if tender_row and tender_row[5] else None,
            },
            "bid_price_model": {
                "version": bid_row[0] if bid_row else None,
                "validation_rmse": float(bid_row[1]) if bid_row and bid_row[1] else None,
                "validation_r2": float(bid_row[2]) if bid_row and bid_row[2] else None,
                "training_samples": bid_row[3] if bid_row else 0,
                "trained_at": str(bid_row[4]) if bid_row and bid_row[4] else None,
                "deployed_at": str(bid_row[5]) if bid_row and bid_row[5] else None,
            },
        }
