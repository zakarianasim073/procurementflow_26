# SEQ-009: Contractor Intelligence & Capacity Analysis

```mermaid
sequenceDiagram
    autonumber
    actor User as Frontend User
    participant API as GET /api/contractors/{id}/capacity
    participant Facade as IntelligenceDataServiceFacade
    participant CS as ContractorService
    participant DNA as ContractorDNAService
    participant DB as PostgreSQL

    User->>API: GET /api/contractors/{id}/capacity
    API->>Facade: get_contractor_profile(id)

    rect rgb(240, 248, 255)
        Note over Facade,CS: Phase 1: Canonical Resolution
        Facade->>DB: SELECT canonical_id FROM canonical_contractors WHERE id=$1 OR alias=$1
        DB-->>Facade: canonical_id (fuzzy match)
        Facade->>DB: SELECT * FROM contractors WHERE canonical_id=$1
        DB-->>Facade: Contractor record
    end

    rect rgb(240, 255, 240)
        Note over Facade,CS: Phase 2: Profile Assembly
        Facade->>CS: build_profile(canonical_id)
        CS->>DB: SELECT COUNT(*) FROM award_records_v2 WHERE contractor=$1
        DB-->>CS: total_projects
        CS->>DB: SELECT completion_rate, on_time_rate, avg_delay FROM contractor_dna
        DB-->>CS: DNA metrics
        CS->>DB: SELECT * FROM contractor_capacity
        DB-->>CS: Capacity data
        CS->>CS: execution_score, reliability_score
        CS-->>Facade: Full profile
    end

    rect rgb(255, 248, 240)
        Note over Facade,DNA: Phase 3: Financial Risk Assessment
        Facade->>DNA: assess_financial_risk(canonical_id)
        DNA->>DB: SELECT annual_turnover, running_contracts FROM contractor_finance
        DB-->>DNA: Financial data
        DNA->>DB: SELECT tender_value FROM pending_bids
        DB-->>DNA: Pending exposure
        DNA->>DNA: leverage_ratio = (exposure + tender_value) / annual_turnover
        DNA->>DNA: cashflow_projection = inflow - outflow (6 months)
        DNA-->>Facade: { leverage_ratio, cashflow_risk, recommendation }
    end

    rect rgb(248, 240, 255)
        Note over Facade,DB: Phase 4: Leaderboard Ranking
        Facade->>DB: SELECT contractor, score FROM contractor_leaderboard ORDER BY dimension
        DB-->>Facade: Rankings across dimensions
    end

    API-->>User: {
        profile: { total_projects, completion_rate, execution_score },
        capacity: { concurrent, max, utilization },
        financial: { leverage_ratio, recommendation: "CAN_BID" },
        leaderboard: { rank, dimension_scores }
    }
```

## Capacity Metrics

| Metric | Computation | Threshold |
|--------|------------|-----------|
| Concurrent Projects | Running contracts count | Max 8 |
| Workload Ratio | Current / Max | Alert if > 0.85 |
| Available Capacity | Max - Current | Min 1 for new bid |
| Leverage Ratio | Exposure / Annual Turnover | Max 2.0 |

## Financial Risk Levels

| Leverage | Cashflow | Recommendation |
|----------|----------|----------------|
| < 0.5 | Positive | **CAN_BID** |
| 0.5-1.0 | Neutral | **RISKY_BID** |
| > 1.0 | Negative | **OVERLEVERAGED** |
