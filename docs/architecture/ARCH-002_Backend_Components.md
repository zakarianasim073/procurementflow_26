# ARCH-002: Backend Component Architecture

```mermaid
graph LR
    subgraph "app/api/v1"
        R_AUTH[/auth]
        R_BOQ[/boq]
        R_SOR[/sor]
        R_TENDER[/tender]
        R_AWARD[/awards]
        R_PRICE[/pricing]
        R_COMP[/competitors]
        R_AGENT[/agents]
        R_INTEL[/intel]
        R_EXEC[/executive]
        R_PPR[/ppr2025]
        R_CRAWL[/crawler]
        R_REPORT[/reports]
        R_SEARCH[/search]
    end

    subgraph "app/api/v2"
        V2_ENT[/enterprise]
        V2_SSO[/sso]
        V2_ANALYTICS[/analytics]
        V2_TENDERS[/tenders]
        V2_DOCS[/documents]
    end

    subgraph "app/services"
        S_BOQ[BOQProcessor]
        S_PDF[PDFParser]
        S_SOR[sor_service]
        S_RATE[RateAnalysisEngine]
        S_TDS[TDSExtractor]
        S_PPR[PPREngine]
        S_MATCH[TenderMatchingService]
        S_INTEL[IntelligenceDataServiceFacade]
        S_DNA[ContractorDNAService]
        S_AUDIT[AuditService]
        S_RBAC[RBACService]
        S_WEBHOOK[WebhookService]
    end

    subgraph "app/agents/core"
        C_BRAIN[AgentBrain]
        C_REG[AgentRegistry]
        C_PIPE[IntelligencePipeline]
        C_THOUGHT[ThoughtEngine]
        C_MEM[Memory]
        C_WATCHDOG[Watchdog]
    end

    subgraph "app/models"
        M_TENDER[ProcurementTender]
        M_AWARD[AwardRecord]
        M_BOQ[BOQItem]
        M_SOR[SORRate]
        M_CONTRACTOR[Contractor]
        M_KNOWLEDGE[KnowledgeEntry]
    end

    R_BOQ --> S_BOQ
    R_BOQ --> S_PDF
    R_SOR --> S_SOR
    R_PRICE --> S_RATE
    R_PPR --> S_PPR
    R_AGENT --> C_BRAIN
    C_BRAIN --> C_REG
    C_BRAIN --> C_PIPE
    C_BRAIN --> C_THOUGHT
    C_BRAIN --> C_MEM
    C_REG --> C_WATCHDOG
    S_BOQ --> M_BOQ
    S_SOR --> M_SOR
    S_MATCH --> M_TENDER
    S_DNA --> M_CONTRACTOR
    C_BRAIN --> M_KNOWLEDGE
```

## Router Count

| Category | Count | Status |
|----------|-------|--------|
| V1 Core (loaded at startup) | 8 | Stable |
| V1 Deferred (loaded async) | 36 | Stable |
| V2 (loaded async) | 8 | Active development |
| Brain Router | 1 | Stable |
| **Total** | **53** | |
