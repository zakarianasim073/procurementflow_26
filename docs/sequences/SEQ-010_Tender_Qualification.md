# SEQ-010: Tender Qualification Scoring

```mermaid
sequenceDiagram
    autonumber
    actor User as Frontend User
    participant API as POST /api/tender/{id}/qualify/{cid}
    participant DB as PostgreSQL
    participant Engine as QualificationEngine

    User->>API: POST /api/tender/{tender_id}/qualify/{contractor_id}

    rect rgb(240, 248, 255)
        Note over API,Engine: Phase 1: Data Gathering
        API->>DB: SELECT * FROM procurement_tenders WHERE tender_id=$1
        DB-->>API: Tender details (title, agency, estimated_amount)
        API->>DB: SELECT * FROM award_records_v2 WHERE contractor=$1
        DB-->>API: Contractor awards history
        API->>DB: SELECT * FROM contractor_dna WHERE contractor_id=$1
        DB-->>API: DNA metrics
    end

    rect rgb(240, 255, 240)
        Note over API,Engine: Phase 2: Similar Work Scoring
        API->>Engine: score_similar_work(tender_title, contractor_awards)
        Engine->>Engine: Extract keywords from tender title
        Engine->>Engine: Fuzzy match against award descriptions
        Engine->>Engine: Compute max similarity score (0-100)
        Engine-->>API: { similar_work_score: 85 }
    end

    rect rgb(255, 248, 240)
        Note over API,Engine: Phase 3: Experience Scoring
        API->>Engine: score_experience(contractor_history)
        Engine->>Engine: years_active = max(award_year) - min(award_year) + 1
        Engine->>Engine: similar_contracts = count(similarity > 0.6)
        Engine->>Engine: experience_score = min(100, years×10 + contracts×5)
        Engine-->>API: { experience_score: 75 }
    end

    rect rgb(248, 240, 255)
        Note over API,Engine: Phase 4: Financial Scoring
        API->>Engine: score_financial(contractor_dna, tender_value)
        Engine->>Engine: capacity_ratio = available_capacity / tender_value
        Engine->>Engine: financial_score = min(100, capacity_ratio × 100)
        Engine-->>API: { financial_score: 70 }
    end

    rect rgb(240, 255, 248)
        Note over API,Engine: Phase 5: Track Record Scoring
        API->>Engine: score_track_record(dna)
        Engine->>Engine: track_score = (completion_rate×40 + on_time_rate×30 + reliability×30)
        Engine-->>API: { track_score: 88 }
    end

    rect rgb(255, 240, 248)
        Note over API,DB: Phase 6: Composite & Persist
        API->>API: composite = (similar×30 + experience×25 + financial×25 + track×20) / 100
        API->>API: recommendation = composite≥70 ? "BID" : composite≥50 ? "CONSIDER" : "NO-BID"
        API->>API: Flag risk factors (overleveraged, no similar work, low completion)
        API->>DB: INSERT INTO tender_qualification_scores
    end

    API-->>User: {
        composite_score: 79,
        recommendation: "BID",
        breakdown: { similar: 85, experience: 75, financial: 70, track: 88 },
        risk_factors: []
    }
```

## Scoring Weights

| Dimension | Weight | Source |
|-----------|--------|--------|
| Similar Work | 30% | Keyword fuzzy match on award history |
| Experience | 25% | Years active + similar contracts count |
| Financial | 25% | Capacity relative to tender value |
| Track Record | 20% | DNA: completion rate, on-time, reliability |

## Recommendations

| Score | Recommendation |
|-------|---------------|
| ≥ 70 | **BID** — Strong candidate |
| 50-69 | **CONSIDER** — Review needed |
| < 50 | **NO-BID** — Weak fit |
