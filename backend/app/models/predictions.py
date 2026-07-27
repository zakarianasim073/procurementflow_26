"""ML Model storage and prediction schemas (T-023)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TenderPriceModel(Base):
    """Trained tender price prediction model metadata."""

    __tablename__ = "tender_price_models"

    model_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_version: Mapped[int] = mapped_column(default=1)
    model_type: Mapped[str] = mapped_column(String(50), default="xgboost")  # xgboost, lightgbm
    algorithm: Mapped[str] = mapped_column(String(100), nullable=True)  # version/hyperparams

    # Model performance metrics
    training_rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    training_r2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # R-squared
    validation_rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_r2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Data used for training
    training_samples: Mapped[int] = mapped_column(default=0)
    training_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    training_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Feature info
    feature_count: Mapped[int] = mapped_column(default=0)
    feature_importance_json: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON serialized dict

    # Model state
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    model_blob: Mapped[Optional[bytes]] = mapped_column(nullable=True)  # Pickled model binary

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    trained_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_tender_price_models_active", "is_active"),
        Index("ix_tender_price_models_version", "model_version"),
    )


class BidPriceModel(Base):
    """Trained winning bid price prediction model."""

    __tablename__ = "bid_price_models"

    model_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_version: Mapped[int] = mapped_column(default=1)
    model_type: Mapped[str] = mapped_column(String(50), default="xgboost")
    algorithm: Mapped[str] = mapped_column(String(100), nullable=True)

    # Performance metrics
    training_rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    training_r2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_r2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Training data stats
    training_samples: Mapped[int] = mapped_column(default=0)
    training_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    training_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Features
    feature_count: Mapped[int] = mapped_column(default=0)
    feature_importance_json: Mapped[Optional[str]] = mapped_column(nullable=True)

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    model_blob: Mapped[Optional[bytes]] = mapped_column(nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    trained_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_bid_price_models_active", "is_active"),
        Index("ix_bid_price_models_version", "model_version"),
    )


class PredictionCache(Base):
    """Cache recent predictions to avoid recomputation."""

    __tablename__ = "prediction_cache"

    cache_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Input features (hashed for cache key)
    feature_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA256 of features
    prediction_type: Mapped[str] = mapped_column(String(20), index=True)  # tender_price, bid_price

    # Prediction results
    predicted_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    predicted_price_low: Mapped[Decimal] = mapped_column(Numeric(15, 2))  # Confidence interval low
    predicted_price_high: Mapped[Decimal] = mapped_column(Numeric(15, 2))  # Confidence interval high
    confidence_score: Mapped[float] = mapped_column(Float)  # 0-1

    # Model used
    model_id: Mapped[str] = mapped_column(String(36), index=True)
    model_version: Mapped[int] = mapped_column()

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)  # TTL for cache

    __table_args__ = (
        Index("ix_prediction_cache_lookup", "feature_hash", "prediction_type"),
    )


class PredictionFeedback(Base):
    """Collect actual prices to improve future model training."""

    __tablename__ = "prediction_feedback"

    feedback_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Original prediction
    prediction_id: Mapped[str] = mapped_column(String(36), index=True)
    predicted_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    predicted_low: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    predicted_high: Mapped[Decimal] = mapped_column(Numeric(15, 2))

    # Actual outcome
    actual_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    prediction_error: Mapped[float] = mapped_column(Float)  # (actual - predicted) / predicted

    # Context
    tender_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    contractor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Feedback quality
    is_useful: Mapped[bool] = mapped_column(Boolean, default=True)  # Flag for data quality
    confidence_in_feedback: Mapped[float] = mapped_column(Float, default=1.0)  # 0-1

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("ix_prediction_feedback_prediction", "prediction_id"),
        Index("ix_prediction_feedback_tender", "tender_id"),
    )


class MarketTrendSnapshot(Base):
    """Time series data for market trend analysis (T-024)."""

    __tablename__ = "market_trend_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Dimension: what trend are we tracking?
    zone_id: Mapped[str] = mapped_column(String(10), index=True)
    category_id: Mapped[str] = mapped_column(String(50), index=True)
    agency_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Metric values for the period (day/week/month)
    period_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)  # Start of period
    period_type: Mapped[str] = mapped_column(String(10), default="day")  # day, week, month

    # Price metrics (BDT)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    min_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    max_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    std_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))

    # Volume metrics
    tender_count: Mapped[int] = mapped_column(default=0)
    bid_count: Mapped[int] = mapped_column(default=0)
    avg_bid_count: Mapped[float] = mapped_column(Float, default=0.0)

    # Trend indicators
    price_trend: Mapped[float] = mapped_column(Float)  # YoY or MoM percentage change
    bid_aggressiveness: Mapped[float] = mapped_column(Float, default=1.0)  # avg_bid / tender_value ratio

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("ix_trend_lookup", "zone_id", "category_id", "period_date"),
    )


class TrendDecomposition(Base):
    """Seasonal decomposition of price trends (T-024)."""

    __tablename__ = "trend_decompositions"

    decomp_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # What we're decomposing
    zone_id: Mapped[str] = mapped_column(String(10), index=True)
    category_id: Mapped[str] = mapped_column(String(50), index=True)

    # Decomposition components
    trend_component: Mapped[str] = mapped_column(nullable=True)  # JSON array of (date, value) tuples
    seasonal_component: Mapped[str] = mapped_column(nullable=True)  # JSON seasonal pattern
    residual_component: Mapped[str] = mapped_column(nullable=True)  # JSON residuals

    # Seasonality info
    seasonal_period_days: Mapped[int] = mapped_column(default=365)  # Annual seasonality by default
    peak_season_months: Mapped[str] = mapped_column(nullable=True)  # e.g., "6,7,8" (monsoon season)
    seasonal_strength: Mapped[float] = mapped_column(Float)  # 0-1, how strong is seasonality?

    # Training data info
    lookback_days: Mapped[int] = mapped_column(default=730)  # 2 years
    data_points_used: Mapped[int] = mapped_column(default=0)

    # Quality metrics
    variance_explained: Mapped[float] = mapped_column(Float)  # R² of decomposition
    mae: Mapped[float] = mapped_column(Float)  # Mean absolute error

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    trained_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # Decomposition expires

    __table_args__ = (
        Index("ix_decomp_zone_cat", "zone_id", "category_id"),
    )


class AnomalyDetection(Base):
    """Detected anomalies in pricing trends (T-024)."""

    __tablename__ = "anomaly_detections"

    anomaly_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Where the anomaly was detected
    zone_id: Mapped[str] = mapped_column(String(10), index=True)
    category_id: Mapped[str] = mapped_column(String(50), index=True)
    period_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # Anomaly details
    anomaly_type: Mapped[str] = mapped_column(String(50))  # spike, drop, deviation, outlier
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high, critical
    confidence: Mapped[float] = mapped_column(Float)  # 0-1, how confident is this detection?

    # Metric values
    observed_value: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    expected_value: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    deviation_pct: Mapped[float] = mapped_column(Float)  # % deviation from expected

    # Context for investigation
    message: Mapped[str] = mapped_column(String(500), nullable=True)  # Human-readable explanation
    suggested_action: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status tracking
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledgement_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        Index("ix_anomaly_zone_cat_date", "zone_id", "category_id", "detected_at"),
    )
