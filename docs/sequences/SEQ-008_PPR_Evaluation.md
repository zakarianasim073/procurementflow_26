# SEQ-008: PPR 2025 Evaluation & TEC Scoring

```mermaid
sequenceDiagram
    autonumber
    actor User as Evaluation User
    participant API as POST /api/ppr2025/evaluate
    participant ENG as PPREngine
    participant ML as PPRMLService
    participant LERT as LERTPredictionAgent (010b)
    participant DB as PostgreSQL

    User->>API: POST /api/ppr2025/evaluate { tender_id, bids[] }

    rect rgb(240, 248, 255)
        Note over API,ENG: Phase 1: Regime Detection
        API->>ENG: detect_regime(tender_id)
        ENG->>DB: SELECT notice_date FROM procurement_tenders
        DB-->>ENG: notice_date
        ENG->>ENG: Regime = notice_date >= 2025-09-28 ? PPR2025 : PPR2008
        ENG-->>API: { regime: "PPR2025" }
    end

    rect rgb(240, 255, 240)
        Note over API,ENG: Phase 2: TEC Evaluation
        loop For each bid
            API->>ENG: evaluate_tec(bid, ruleset)
            ENG->>ENG: Step 1: Responsiveness Check
            Note over ENG: Document completeness,<br/>format compliance,<br/>signatures present

            ENG->>ENG: Step 2: Arithmetic Check
            Note over ENG: BOQ cross-add verification<br/>Max 20% deviation before rejection

            ENG->>ENG: Step 3: Qualification Check
            Note over ENG: Experience, turnover,<br/>equipment, personnel, licenses

            ENG->>ENG: Step 4: TEC Minimum Pass
            Note over ENG: Per-schedule scoring<br/>Minimum 70% threshold

            ENG->>ENG: Step 5: SLT Threshold
            Note over ENG: SLT = 70% of estimated cost<br/>ALT = 60% of estimated cost

            ENG-->>API: { bid_id, tec_score: 82.5, responsive: true, slt_eligible: true }
        end
    end

    rect rgb(255, 248, 240)
        Note over API,ML: Phase 3: ML Prediction
        API->>ML: predict_bid_amount(tender_id, features)
        ML->>DB: SELECT historical awards WHERE agency = $1
        DB-->>ML: Training data
        ML->>ML: Feature engineering (NPP index, zone, work_type, agency)
        ML->>ML: Predict with sklearn model (cached 15min)
        ML-->>API: { predicted_amount: 45000000, confidence: 0.78 }
    end

    rect rgb(248, 240, 255)
        Note over API,LERT: Phase 4: LERT Prediction
        API->>LERT: predict_lert(tender_id, bids_with_scores)
        LERT->>LERT: Filter responsive bids only
        LERT->>LERT: Rank by evaluated amount
        LERT-->>API: { lert_bidder: "Contractor A", lert_amount: 42000000 }
    end

    API->>DB: Persist ppr_evaluations (scores, rationale, evidence)
    API-->>User: { evaluations[], lert_prediction, ml_prediction, regime }
```

## TEC Evaluation Rules

| Check | PPR 2025 Rule | Threshold |
|-------|--------------|-----------|
| Arithmetic Error | Max deviation before rejection | 20% |
| TEC Minimum Pass | Per-schedule score | 70% |
| SLT Threshold | Lowest 70% of estimated | 70% |
| ALT Threshold | Lowest 60% of estimated | 60% |
| Qualification | Experience + Turnover | Per TDS |
