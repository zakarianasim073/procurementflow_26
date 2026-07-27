# SEQ-006: Bid/No-Bid Decision Engine

```mermaid
sequenceDiagram
    autonumber
    actor User as Executive User
    participant API as POST /api/agents/agent-039/run
    participant Agent as BidNoBidAgent (agent-039)
    participant WP as WinProbabilityAgent (016)
    participant BPO as BidPositionOptimizer (017)
    participant ED as ExecutiveDecisionAgent (022)
    participant FI as FinancialIntelligence (021)
    participant RC as ResourceCapacity (019)
    participant DB as PostgreSQL

    User->>API: Execute bid/no-bid for tender_id
    API->>Agent: run({ tender_id, company_context })

    rect rgb(240, 248, 255)
        Note over Agent,WP: Phase 1: Win Probability
        Agent->>WP: execute({ tender_id, competitors, history })
        WP->>DB: SELECT awards WHERE contractor_id = $1
        DB-->>WP: Historical wins/losses
        WP->>DB: SELECT agency performance
        DB-->>WP: Agency match data
        WP->>WP: Compute: Base(50%) × AgencyMatch × History / (CompetitionRisk × DiscountPosition)
        WP->>WP: Enhance with ML prediction (cached model)
        WP-->>Agent: { win_probability: 0.68, confidence: 0.75 }
    end

    rect rgb(240, 255, 240)
        Note over Agent,BPO: Phase 2: Bid Position
        Agent->>BPO: execute({ tender_id, win_prob, margin_target })
        BPO->>DB: SELECT competitor_discount_patterns
        DB-->>BPO: Historical discount data
        BPO->>BPO: Generate 3 scenarios
        BPO-->>Agent: { AGGRESSIVE: [15,20]%, MODERATE: [8,12]%, CONSERVATIVE: [3,7]% }
    end

    rect rgb(255, 248, 240)
        Note over Agent,FI: Phase 3: Financial Capacity
        Agent->>FI: execute({ tender_id, tender_value })
        FI->>DB: SELECT contractors, contractor_dna, award_records_v2
        DB-->>FI: Financial profile
        FI->>FI: Compute leverage ratio, cashflow projection
        FI-->>Agent: { can_fund: true, leverage_ratio: 0.65, risk_level: "MODERATE" }
    end

    rect rgb(248, 240, 255)
        Note over Agent,RC: Phase 4: Resource Capacity
        Agent->>RC: execute({ tender_id, required_resources })
        RC->>DB: SELECT contractor_capacity
        DB-->>RC: Current workload
        RC->>RC: Compute: available_capacity / required
        RC-->>Agent: { capacity_ok: true, utilization: 0.72 }
    end

    rect rgb(240, 255, 248)
        Note over Agent,ED: Phase 5: Final Decision
        Agent->>ED: execute({ wp, bpo, fi, rc })
        ED->>ED: Composite Bid Score:<br/>WP(35%) + Margin(25%) + Competition(15%) + Capacity(10%) + Cashflow(10%) + Strategic(5%)
        ED-->>Agent: { score: 78.5, decision: "BID", confidence: 0.82 }
    end

    Agent->>DB: Persist decision + rationale
    Agent-->>User: { decision: "BID", score: 78.5, discount_range: [8,12]%, rationale: "..." }
```

## Scoring Formula

```
Composite Score = (WinProbability × 35) + (MarginScore × 25) + (CompetitionScore × 15) + (CapacityScore × 10) + (CashflowScore × 10) + (StrategicScore × 5)
```

| Score Range | Decision |
|-------------|----------|
| ≥ 75 | **BID** — High confidence |
| 60-74 | **REVIEW** — Needs human review |
| < 60 | **NO-BID** — Skip opportunity |
