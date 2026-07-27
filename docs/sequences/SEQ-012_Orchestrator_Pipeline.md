# SEQ-012: Multi-Agent Orchestrator Pipeline (14 Phases)

```mermaid
sequenceDiagram
    autonumber
    participant API as POST /api/brain/workflow
    participant Orch as WorkflowOrchestrator (agent-027)
    participant Reg as AgentRegistry
    participant Brain as AgentBrain
    participant KB as Knowledge Entries

    API->>Orch: execute({ mode: "full", tender_id })
    Orch->>Reg: get_pipeline("full")

    rect rgb(240, 248, 255)
        Note over Orch,Reg: Phase 1-2: DISCOVERY + PRE_SCREEN
        Orch->>Reg: run_pipeline(["agent-001", "agent-002", "agent-003"])
        Reg->>Brain: execute(agent-001, scan)
        Brain-->>Reg: { tenders: 12 }
        Reg->>Brain: execute(agent-002, acquire)
        Brain-->>Reg: { acquired: 5 }
        Reg->>Brain: execute(agent-038, prescreen)
        Brain-->>Reg: { qualified: 3 }
    end

    rect rgb(240, 255, 240)
        Note over Orch,Reg: Phase 3: INTELLIGENCE
        Orch->>Reg: run_pipeline(["agent-004", "agent-005", "agent-006"])
        Reg->>Brain: execute(agent-005, parse_boq)
        Brain-->>Reg: { items: 45 }
    end

    rect rgb(255, 248, 240)
        Note over Orch,Reg: Phase 4: EVALUATION
        Orch->>Reg: run_pipeline(["agent-046", "agent-007", "agent-008", "agent-009", "agent-010b", "agent-010"])
        Note over Reg: DataQuality → Eligibility → Risk → PPR → LERT → Compliance
    end

    rect rgb(248, 240, 255)
        Note over Orch,Reg: Phase 5: PRICING
        Orch->>Reg: run_pipeline(["agent-011", "agent-012", "agent-048", "agent-049", "agent-044", "agent-033"])
        Note over Reg: RateAnalysis → MarketRate → MaterialCrawler → MaterialMargin → ZoneMatcher → VatTax
    end

    rect rgb(255, 240, 240)
        Note over Orch,Reg: Phase 6: COMPETITOR
        Orch->>Reg: run_pipeline(["agent-013", "agent-014", "agent-015", "agent-016", "agent-017", "agent-028", "agent-036"])
        Note over Reg: CompetitorIntel → AwardIntel → PricingPredict → WinProb → BidPosition → Syndicate → MOAT
    end

    rect rgb(240, 255, 248)
        Note over Orch,Reg: Phase 7-8: DECISION + EXECUTION
        Orch->>Reg: run_pipeline(["agent-018", "agent-019", "agent-021", "agent-022", "agent-039", "agent-043"])
        Note over Reg: BidAssistant → Capacity → Financial → Executive → BidNoBid → Client
        Orch->>Reg: run_pipeline(["agent-020", "agent-024", "agent-034", "agent-032", "agent-031", "agent-035"])
        Note over Reg: EGP_RateFill → Submission → Document → DocPrep → TenderPrep → Dashboard
    end

    rect rgb(255, 255, 240)
        Note over Orch,Reg: Phase 9-14: REPORTING → LEARNING → KNOWLEDGE → FORECAST → POST_AWARD → ALERTING
        Orch->>Reg: run_pipeline(["agent-023", "agent-026", "agent-025", "agent-042", "agent-045", "agent-003"])
    end

    Orch->>KB: Store pipeline completion summary
    Orch-->>API: { status: "completed", phases_completed: 14, agents_executed: 49 }
```

## Pipeline Phases

| Phase | Agents | Purpose |
|-------|--------|---------|
| 1. Discovery | 001, 002, 003 | Find + acquire tenders |
| 2. Pre-Screen | 038 | Narrow to qualified candidates |
| 3. Intelligence | 004, 005, 006 | Parse documents |
| 4. Evaluation | 046, 007, 008, 009, 010b, 010 | Compliance + risk |
| 5. Pricing | 011, 012, 048, 049, 044, 033 | Rate analysis |
| 6. Competitor | 013, 014, 015, 016, 017, 028, 036 | Competition intel |
| 7. Decision | 018, 019, 021, 022, 039, 043 | Bid/No-Bid |
| 8. Execution | 020, 024, 034, 032, 031, 035 | Tender prep |
| 9. Reporting | 023 | Report generation |
| 10. Learning | 026 | Outcome tracking |
| 11. Knowledge | 025 | Knowledge lake |
| 12. Forecast | 042 | APP forecasting |
| 13. Post-Award | 045 | Opening reports |
| 14. Alerting | 003 | Watchdog alerts |
