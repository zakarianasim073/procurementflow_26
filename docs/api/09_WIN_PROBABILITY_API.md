# Win Probability API Contract

**Router**: `/api/v1/win-probability` (v1) / `/api/v2/win-probability` (v2 enterprise)  
**Tags**: `win-probability`  
**Auth**: JWT (tenant-scoped)

---

## Overview

Win Probability API for **bid success prediction**, **tender outcome forecasting**, and **intelligent bidding strategy** in the construction procurement workflow. Integrates **ML predictions**, **SOR matching**, **competitor intelligence**, and **PPR2025 compliance** to calculate and optimize win probabilities for each tender opportunity.

**Primary Use Cases**:
- Calculate win probability for specific tenders
- Optimize bid discounts for target win probability
- Benchmark against historical win rates and market trends
- Generate win probability reports for executive decision support
- Trigger automated bid strategy recommendations

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------||------|
| GET | `/win-probability/analyze/{tender_id}` | Calculate win probability for tender | JWT |
| POST | `/win-probability/predict` | AI/ML prediction for tender bid | JWT |
| GET | `/win-probability/benchmarks` | Get win probability benchmarks by agency/zone | JWT |
| GET | `/win-probability/trends` | Historical win probability trends | JWT |
| POST | `/win-probability/optimize` | Optimize bid strategy for target win probability | JWT |

---

## Request/Response Schemas

### `GET /win-probability/analyze/{tender_id}`

**Path Params**
- `tender_id`: Tender identifier (e.g., "1298004")

**Response (200)**
```json
{
  "success": true,
  "tender_id": "1298004",
  "win_probability": {
    "overall": 0.71,
    "confidence": "High",
    "model_type": "hybrid_ml",
    "factors": {
      "sor_match_rate": 0.78,
      "competitor_count": 3,
      "budget_alignment": 0.92,
      "past_performance": 0.85,
      "regime_compliance": 0.94
    },
    "ml_prediction": {
      "probability": 0.73,
      "model_id": "ppr_ml_v2.1",
      "training_accuracy": 0.87,
      "last_trained": "2026-06-15T10:30:00Z"
    },
    "heuristic": {
      "base_rate": 0.65,
      "adjustments": {
        "match_bonus": 0.08,
        "competitor_penalty": -0.02,
        "budget_bonus": 0.04
      },
      "predicted": 0.73
    },
    "recommendation": {
      "target_bid": 0.47,
      "bid_strategy": "competitive",
      "win_probability_improvement": "low"
    },
    "timestamp": "2026-07-21T12:00:00Z"
  },
  "input_data": {
    "tender_id": "1298004",
    "package_no": "BWDB-CTG-01/2024-25",
    "estimated_cost": 45000000,
    "tender_security": 450000,
    "procuring_entity": "BWDB Dhaka Division",
    "bidder_count": 4,
    "competitor_profile": "Mid-size civil contractor",
    "budget_alignment": 0.92,
    "past_performance": 0.85
  },
  "execution_metrics": {
    "sor_lookups": 245,
    "competitor_queries": 12,
    "ml_inference_time_ms": 1250,
    "overall_processing_ms": 3750
  }
}
```

### `POST /win-probability/predict`

**Request**
```json
{
  "tender_id": "1298004",
  "bid_price": 38500000,
  "estimated_cost": 45000000,
  "bidder_experience": 12,
  "competitor_standings": [
    {
      "name": "Skyatech Ltd",
      "bid_price": 42000000,
      "experience_years": 8,
      "win_rate_last_year": 0.68
    },
    {
      "name": "BuildRight Asia",
      "bid_price": 39500000,
      "experience_years": 5,
      "win_rate_last_year": 0.52
    }
  ],
  "regime_compliance": {
    "slt_status": "passed",
    "ppr2025_compliance": true,
    "document_status": "complete"
  },
  "market_context": {
    "average_bid_range": {
      "min": 35000000,
      "max": 48000000
    },
    "zone_market_premium": 0.08,
    "competitor_density": 3
  },
  "user_profile": {
    "contractor_type": "medium",
    "capacity_utilization": 0.75,
    "risk_tolerance": "moderate"
  }
}
```

**Response (200)**
```json
{
  "success": true,
  "prediction": {
    "win_probability": 0.71,
    "confidence": "High",
    "model_type": "hybrid_ml",
    "ml_probabilities": {
      "isolation_forest": 0.68,
      "random_forest": 0.73,
      "gradient_boosting": 0.70,
      "neural_network": 0.75
    },
    "ensemble_score": 0.72,
    "outlier_detection": {
      "flagged": false,
      "reason": "All features within normal range"
    }
  },
  "factors": {
    "financial_factors": {
      "budget_alignment": 0.92,
      "price_positioning": "competitive",
      "risk_assessment": "medium"
    },
    "competitor_factors": {
      "number_of_competitors": 4,
      "average_competitor_win_rate": 0.58,
      "experience_profile_match": 0.64
    },
    "regulatory_factors": {
      "slt_compliance": 1.0,
      "ppr2025_compliance": 1.0,
      "document_completeness": 1.0
    }
  },
  "bid_recommendation": {
    "suggested_bid": 38500000,
    "optimal_bid_range": {
      "min": 35000000,
      "max": 42000000
    },
    "win_probability_target": 0.65,
    "strategy": "competitive",
    "pricing_approach": "market_aligned"
  },
  "risk_analysis": {
    "volatility_score": 0.23,
    "confidence_interval": {
      "lower": 0.62,
      "upper": 0.78
    },
    "sensitivity_analysis": {
      "competitor_count_plus_1": 0.68,
      "price_increase_5pc": 0.64,
      "budget_decrease_10pc": 0.76
    }
  },
  "model_insights": {
    "top_predictors": [
      "budget_alignment",
      "competitor_count",
      "company_experience"
    ],
    "feature_weights": {
      "budget_alignment": 0.35,
      "company_experience": 0.23,
      "regime_compliance": 0.18
    }
  },
  "validation": {
    "model_age": "45 days",
    "validation_metrics": {
      "accuracy": 0.87,
      "precision": 0.85,
      "recall": 0.82
    },
    "data_qualiy_score": 0.91
  }
}
```

### `GET /win-probability/benchmarks`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `agency` | string | null | Filter by agency (BWDB, PWD, LGED) |
| `zone` | string | null | Filter by zone (A, B, C, D) |
| `years` | int | 5 | Historical span (1-10) |

**Response (200)**
```json
{
  "success": true,
  "benchmarks": {
    "by_agency": [
      {
        "agency": "BWDB",
        "zone": "A",
        "win_probability_range": {
          "min": 0.45,
          "max": 0.78,
          "average": 0.62
        },
        "success_count": 847,
        "total_tenders": 1247,
        "competitor_density": 2.8,
        "avg_bid_vs_budget_ratio": 0.87
      }
    ],
    "by_zone": [
      {
        "zone": "A",
        "win_probability": 0.62,
        "competitor_count": 2.1,
        "avg_bid_discount": 8.4,
        "bid_variance": 0.15,
        "opportunity_count": 387
      }
    ],
    "historical_trends": [
      {
        "month": "2026-01",
        "overall_win_probability": 0.58,
        "agency_breakdown": {
          "BWDB": 0.62,
          "PWD": 0.51,
          "LGED": 0.48
        }
      }
    ]
  },
  "statistics": {
    "total_tenders_analyzed": 12500,
    "prediction_accuracy": 0.87,
    "model_confidence_scores": {
      "high": 234,
      "medium": 487,
      "low": 123
    }
  }
}
```

### `POST /win-probability/optimize`

**Request**
```json
{
  "tender_id": "1298004",
  "target_win_probability": 0.75,
  "current_bid": 38500000,
  "estimated_cost": 45000000,
  "optimization_objective": "minimize_bid",
  "constraints": {
    "max_bid_increase_percent": 15,
    "min_budget_alignment": 0.85,
    "competitor_profile_required": true
  },
  "scenario_sensitivity": true
}
```

**Response (200)**
```json
{
  "success": true,
  "optimization_result": {
    "optimal_bid": 38925000,
    "win_probability_achieved": 0.76,
    "bid_improvement": {
      "amount": 425000,
      "percentage": 1.10
    },
    "strategy": {
      "approach": "competitive_positioning",
      "rationale": "Slight bid increase for 12% higher win probability"
    },
    "feasibility_analysis": {
      "is_feasible": true,
      "constraints_met": {
        "bid_increase_percent": 1.10,
        "budget_alignment": 0.93,
        "competitor_profile": true
      }
    },
    "sensitivity_scenarios": {
      "competitor_increase": {
        "scenario": "competitors + 1",
        "win_probability": 0.74,
        "bid": 38850000
      },
      "budget_reduction": {
        "scenario": "budget -5%",
        "win_probability": 0.71,
        "bid": 36875000
      }
    }
  },
  "alternative_strategies": [
    {
      "strategy": "aggressive",
      "bid": 34500000,
      "win_probability": 0.58,
      "risk_rating": "high"
    },
    {
      "strategy": "balanced",
      "bid": 37000000,
      "win_probability": 0.64,
      "risk_rating": "medium"
    }
  ],
  "execution_plan": {
    "immediate_action": "submit_bid_with_optimized_price",
    "monitoring": "track_win_outcome_30_days",
    "adjustment_rules": "auto_adjust_if_win_rate_2x_deviation"
  }
}
```

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `WIN_PROBABILITY_NOT_FOUND` | 404 | Tender ID not found |
| `WIN_PROBABILITY_INVALID_INPUT` | 400 | Invalid prediction request |
| `WIN_PROBABILITY_MODEL_ERROR` | 500 | ML model inference failed |

---

## Permission Requirements

| Endpoint | Role | Notes |
|----------|------|-------|
| `/analyze/{tender_id}` | `viewer` or higher | Read win probability |
| `/predict` | `estimator` or `admin` | Generate ML predictions |
| `/optimize` | `estimator` or `admin` | Optimize bid strategy |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/analyze` | 30 | 60 |
| `/predict` | 20 | 60 |
| `/optimize` | 10 | 60 |
| `/benchmarks` | 60 | 60 |
| `/trends` | 30 | 60 |

---

## Caching

- `GET /analyze/{tender_id}`: `private, max-age=300` (ML cache)
- `GET /benchmarks`, `GET /trends`: `private, max-age=1800` (hourly updates)
- Other: `private, max-age=600` (custom optimization results)

---

## React Query Mapping

```typescript
export const winProbKeys = {
  all: () => ['win-probability'] as const,
  analyze: (tenderId: string) => [...winProbKeys.all, 'analyze', tenderId] as const,
  predict: () => [...winProbKeys.all, 'predict'] as const,
  benchmarks: (params?: BenchmarkParams) =>
    [...winProbKeys.all, 'benchmarks', { params }] as const,
  trends: (params?: TrendsParams) =>
    [...winProbKeys.all, 'trends', { params }] as const,
  optimize: () => [...winProbKeys.all, 'optimize'] as const,
};

export function useWinProbability(tenderId: string) {
  return useQuery({
    queryKey: winProbKeys.analyze(tenderId),
    queryFn: () => apiFetch<WinProbabilityResponse>(`/win-probability/analyze/${tenderId}`),
    staleTime: 60_000,
  });
}

export function useWinProbabilityPrediction() {
  return useMutation({
    mutationFn: (data: PredictRequest) => apiFetch<PredictionResponse>('/win-probability/predict', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  });
}
```

---

## Integration Points

### Tender Radar Integration
```
Agent-001-TenderRadar → Extract tender info → 
  POST /win-probability/analyze/{tender_id} → 
    Calculate win probability → 
      Display in dashboard with color-coded indicators
```

### Pricing + Win Probability
```
POST /boq/compare → BOQ + SOR results → 
  POST /pricing/rate-analysis/from-compare → Rate analysis → 
    POST /win-probability/predict → Optimized win probability → 
      Adjust bid strategy for target win probability
```

### Executive Decision Support
```
GET /executive/overview → Executive dashboard → 
  Include win probability metrics for each tender → 
    Enable "Bidding Recommended" vs "Do Not Bid" decisions
```

---

## Formula & Model

**Hybrid Model (70% Machine Learning + 30% Heuristic)**:

### ML Component (70%)
- **Isolation Forest**: Anomaly detection among tender characteristics
- **Random Forest**: Ensemble of decision trees for feature importance
- **Gradient Boosting**: Sequential ensemble for prediction
- **Neural Network**: Non-linear relationships and complex patterns

### Heuristic Component (30%)
- **SOR Match Rate**: Relevance of rate analysis (% items matched)
- **Competitor Density**: Number of bidders (inverse correlation)
- **Budget Alignment**: Bid relative to budget (optimal range: 85-95%)
- **Past Performance**: Company track record
- **Regime Compliance**: PPR2025 compliance score

### Integration Formula
```
win_probability = round(
  0.70 * ml_model_score + 
  0.30 * heuristic_score,
  2
)
```

### Configuration
- **ML Threshold**: Only use ML if confidence > 0.85
- **Fallback**: Heuristic when ML unavailable
- **Calibration**: Annual model retraining with new data
- **Ensemble**: Multiple model averaging

---

## Monitoring & Telemetry

**Metrics**:
- Prediction accuracy (vs actual outcomes)
- ML model inference time and confidence
- Heuristic component contribution
- Bid strategy success rates
- Model drift detection

**Alerts**:
- Prediction accuracy < 0.75
- ML confidence < 0.8
- Model change detection
- Anomalous feature patterns

> **Dependency**: `app/services/ppr_ml_service.py` (ML model management)
> **Integration**: `app/agents/competitor.py` (competitor intelligence for predictions)
> **Data**: `procurement_lifecycle` table (historical win outcomes)

---

## Versioning

- `v1`: Current (ML + heuristic hybrid)
- `v2` (planned): Real-time prediction updates, reinforcement learning

---

## Configuration Options

Environment variables:
- `WIN_PROBABILITY_ML_THRESHOLD=0.85` (default: 0.85)
- `WIN_PROBABILITY_HEURISTIC_WEIGHT=0.3` (default: 0.3)
- `WIN_PROBABILITY_CACHE_TTL=3600` (seconds)
- `WIN_PROBABILITY_MODEL_UPDATE_FREQUENCY=30` (days)

---

## OpenAPI Reference

See `/openapi.json#/paths/~1api~1win-probability~1analyze~1{tender_id}~1GET`