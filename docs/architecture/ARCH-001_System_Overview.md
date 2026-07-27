# ARCH-001: System Architecture Overview

```mermaid
graph TB
    subgraph "Frontend (SPA)"
        FE[React 19 + TypeScript<br/>Feature-Sliced Design]
    end

    subgraph "API Gateway"
        GW[FastAPI<br/>Port 8000]
        MW[Middleware Stack<br/>CORS · Rate Limit · Auth · Audit]
    end

    subgraph "Core Services"
        BOQ[BOQ Service<br/>PDF Parser + SOR Matching]
        SOR[SOR Service<br/>3 Agencies · 4545 Rates]
        PRICING[Pricing Service<br/>Market Index + Templates]
        SEARCH[Search Service<br/>PostgreSQL FTS + pg_trgm]
        PPR[PPR Engine<br/>2008/2025 Rules]
    end

    subgraph "Agent Runtime"
        BRAIN[AgentBrain<br/>Central Orchestrator]
        REG[AgentRegistry<br/>49 Agents]
        PIPE[IntelligencePipeline<br/>14 Phases]
        THOUGHT[ThoughtEngine<br/>Human-in-the-Loop]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL 17<br/>Port 5433)]
        REDIS[(Redis<br/>Cache + Locks)]
        FS[File Storage<br/>uploads/]
        VDB[(Vector DB<br/>Embeddings)]
    end

    subgraph "External"
        EGP[e-GP Portal<br/>eprocure.gov.bd]
        MATERIAL[Material Price<br/>BD Market Sites]
    end

    FE -->|HTTP/REST| GW
    GW --> MW
    MW --> BOQ
    MW --> SOR
    MW --> PRICING
    MW --> SEARCH
    MW --> PPR
    MW --> BRAIN
    BRAIN --> REG
    BRAIN --> PIPE
    BRAIN --> THOUGHT
    BOQ --> PG
    BOQ --> SOR
    SOR --> PG
    PRICING --> PG
    SEARCH --> PG
    PPR --> PG
    BRAIN --> REDIS
    BRAIN --> VDB
    BOQ --> FS
    REG --> EGP
    REG --> MATERIAL
```

## Components

| Layer | Components | Responsibility |
|-------|-----------|---------------|
| Frontend | React 19 SPA | UI rendering, state management, API calls |
| API Gateway | FastAPI + Middleware | Request routing, auth, rate limiting, audit |
| Core Services | BOQ, SOR, Pricing, Search, PPR | Domain logic |
| Agent Runtime | Brain, Registry, Pipeline, Thought | AI orchestration |
| Data Layer | PostgreSQL, Redis, FS, VectorDB | Persistence |
| External | e-GP, Material Sites | Data sources |
