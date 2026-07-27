# SEQ-014: Executive Intelligence Report

```mermaid
sequenceDiagram
    autonumber
    actor User as Executive User
    participant API as GET /api/executive/report
    participant Facade as IntelligenceDataServiceFacade
    participant ML as PPRMLService
    participant MOAT as MOATSLTAnalyzerAgent
    participant DB as PostgreSQL

    User->>API: GET /api/executive/report

    rect rgb(240, 248, 255)
        Note over API,Facade: Phase 1: Aggregate Metrics
        API->>Facade: get_overview()
        Facade->>DB: SELECT COUNT(*), SUM(value) FROM award_records_v2
        DB-->>Facade: total awards, total value
        Facade->>DB: SELECT COUNT(DISTINCT contractor) FROM award_records_v2
        DB-->>Facade: total contractors
        Facade->>DB: SELECT agency, COUNT(*) FROM procurement_tenders GROUP BY agency
        DB-->>Facade: agency distribution
        Facade->>DB: SELECT AVG(discount_pct) FROM award_records_v2
        DB-->>Facade: avg discount
        Facade-->>API: overview metrics
    end

    rect rgb(240, 255, 240)
        Note over API,DB: Phase 2: Pipeline Data
        API->>DB: SELECT year, agency, COUNT(*) FROM procurement_tenders GROUP BY year, agency
        DB-->>API: tender trends by agency/year
        API->>DB: SELECT npp_index FROM npp_trends ORDER BY month
        DB-->>API: NPP trend data
        API->>DB: SELECT discount_range, COUNT(*) FROM award_records_v2 GROUP BY discount_range
        DB-->>API: discount distribution
    end

    rect rgb(255, 248, 240)
        Note over API,ML: Phase 3: ML Prediction
        API->>ML: predict_bid_range(tender_features)
        ML->>DB: SELECT historical awards WHERE agency=$1 AND zone=$2
        DB-->>ML: training subset
        ML->>ML: Predict with cached model (15min TTL)
        ML-->>API: { predicted_range: [42M, 48M], confidence: 0.78 }
    end

    rect rgb(248, 240, 255)
        Note over API,MOAT: Phase 4: SLT Intelligence
        API->>MOAT: analyze_slt_tenders()
        MOAT->>DB: SELECT agency, MIN(evaluated_amount) FROM tender_evaluations
        DB-->>MOAT: SLT thresholds per agency
        MOAT->>DB: SELECT discount_pct, agency FROM award_records_v2
        DB-->>MOAT: discount patterns
        MOAT->>MOAT: Compute recommended discount (NPPI-weighted)
        MOAT-->>API: { slt_thresholds, recommended_discount: 12.5 }
    end

    rect rgb(255, 240, 240)
        Note over API,DB: Phase 5: Competitor Landscape
        API->>DB: SELECT contractor, SUM(value), COUNT(*) FROM award_records_v2 GROUP BY contractor ORDER BY SUM(value) DESC LIMIT 10
        DB-->>API: top 10 contractors
        API->>DB: SELECT contractor, win_rate FROM contractor_leaderboard
        DB-->>API: win rates
    end

    API-->>User: {
        overview: { total_awards, total_value, avg_discount },
        pipeline: { trends, npp, discount_distribution },
        ml_prediction: { range, confidence },
        slt: { thresholds, recommended_discount },
        competitors: { top_10, win_rates }
    }
```

## Report Sections

| Section | Data Source | Refresh |
|---------|-----------|---------|
| Overview | Award aggregations | Real-time |
| Pipeline | Tender trends | Real-time |
| ML Prediction | Historical awards (sklearn) | Cached 15min |
| SLT Intelligence | Evaluation thresholds | Real-time |
| Competitor Landscape | Award records | Real-time |
