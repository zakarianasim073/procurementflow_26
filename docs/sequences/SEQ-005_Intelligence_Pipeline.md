# SEQ-005: Intelligence Pipeline (Full Agent Chain)

```mermaid
sequenceDiagram
    autonumber
    participant API as POST /api/brain/pipeline/run
    participant Pipe as IntelligencePipeline
    participant Brain as AgentBrain
    participant A001 as TenderRadar (001)
    participant A002 as TenderAcquisition (002)
    participant A005 as BOQIntelligence (005)
    participant A007 as EligibilityCompliance (007)
    participant A012 as MarketRate (012)
    participant A013 as CompetitorIntel (013)
    participant A016 as WinProbability (016)
    participant A017 as BidPosition (017)
    participant A022 as ExecutiveDecision (022)
    participant KB as Knowledge Entries

    API->>Pipe: run(mode="intelligence")
    Pipe->>Brain: Initialize pipeline context

    rect rgb(240, 248, 255)
        Note over Pipe,A001: Phase 1: DISCOVERY
        Pipe->>A001: execute({ action: "scan_live_tenders" })
        A001-->>Pipe: { tenders_found: 12, new: 5 }
        Pipe->>A002: execute({ tender_ids: [...] })
        A002-->>Pipe: { acquired: 3, failed: 2 }
    end

    rect rgb(240, 255, 240)
        Note over Pipe,A005: Phase 2: INTELLIGENCE
        loop For each acquired tender
            Pipe->>A005: execute({ tender_id })
            A005-->>Pipe: { items_parsed: 45, categories: [...] }
        end
    end

    rect rgb(255, 248, 240)
        Note over Pipe,A007: Phase 3: EVALUATION
        Pipe->>A007: execute({ tender_id, company_profile })
        A007-->>Pipe: { eligible: true, score: 82, gaps: [...] }
    end

    rect rgb(248, 240, 255)
        Note over Pipe,A012: Phase 4: PRICING
        Pipe->>A012: execute({ tender_id, boq_items })
        A012-->>Pipe: { market_rates: [...], margins: [...] }
    end

    rect rgb(255, 240, 240)
        Note over Pipe,A013: Phase 5: COMPETITOR
        Pipe->>A013: execute({ tender_id, agency })
        A013-->>Pipe: { competitors: 8, avg_discount: 12.5 }
        Pipe->>A016: execute({ tender_id, competitors })
        A016-->>Pipe: { win_probability: 0.68 }
        Pipe->>A017: execute({ tender_id, win_prob, margin_target })
        A017-->>Pipe: { discount_range: [8, 15], recommended: 12 }
    end

    rect rgb(240, 255, 248)
        Note over Pipe,A022: Phase 6: DECISION
        Pipe->>A022: execute({ all_upstream_results })
        A022-->>Pipe: { decision: "BID", confidence: 0.82, rationale: "..." }
    end

    Pipe->>KB: Store pipeline results as knowledge_entries
    Pipe-->>API: PipelineResult { status, tender_results[] }
```

## Pipeline Stages

| Stage | Agents | Output |
|-------|--------|--------|
| Discovery | 001, 002 | Tender list + acquired documents |
| Intelligence | 005 | Parsed BOQ items |
| Evaluation | 007 | Eligibility score |
| Pricing | 012 | Market rates + margins |
| Competitor | 013, 016, 017 | Competition analysis + bid position |
| Decision | 022 | Bid/No-Bid recommendation |

## Timing

| Phase | Duration |
|-------|----------|
| Discovery | 60-180s |
| Intelligence | 30-60s |
| Evaluation | 5-10s |
| Pricing | 10-20s |
| Competitor | 10-20s |
| Decision | 5-10s |
| **Total** | **120-300s** |

## Error Paths

1. **Agent timeout** — Pipeline marks stage as FAILED, continues with remaining stages
2. **Agent exception** — Logged, upstream context partially populated, decision uses available data
3. **All agents fail** — Pipeline returns status: DEGRADED with partial results
