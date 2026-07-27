# ARCH-009: Data Flow Architecture

```mermaid
graph LR
    subgraph "Data Sources"
        EGP_S[e-GP Portal<br/>395K tenders]
        CRAWL_S[Crawler Plugins<br/>Multi-source]
        UPLOAD_S[User Uploads<br/>BOQ PDFs]
        MATERIAL_S[Material Sites<br/>BD Market]
    end

    subgraph "Ingestion Layer"
        RADAR[agent-001<br/>TenderRadar]
        ACQ[agent-002<br/>Acquisition]
        CRAWL_O[CrawlerOrchestrator]
        UPLOAD_API[/api/boq/upload]
    end

    subgraph "Processing Layer"
        PDF_P[PDFParser<br/>pdfplumber]
        BOQ_P[BOQProcessor<br/>SOR Matching]
        TDS_E[TDSExtractor<br/>Regex Parsing]
        RATE_E[RateAnalysisEngine<br/>Cost Breakdown]
        PPR_E[PPREngine<br/>Compliance Rules]
    end

    subgraph "Storage Layer"
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        FS[(File System)]
        VDB[(Vector DB)]
    end

    subgraph "Intelligence Layer"
        COMP_I[Competitor Intelligence]
        WIN_P[Win Probability]
        BID_O[Bid Position]
        EXEC_D[Executive Decision]
    end

    subgraph "Output Layer"
        API_R[/api/* endpoints]
        EXCEL[Excel Reports]
        DASH[Executive Dashboard]
        NOTIFY[Webhook Notifications]
    end

    EGP_S --> RADAR
    EGP_S --> ACQ
    CRAWL_S --> CRAWL_O
    UPLOAD_S --> UPLOAD_API

    RADAR --> PG
    ACQ --> PDF_P
    ACQ --> FS
    UPLOAD_API --> PDF_P
    CRAWL_O --> PG

    PDF_P --> BOQ_P
    PDF_P --> TDS_E
    BOQ_P --> PG
    TDS_E --> PG
    RATE_E --> PG
    PPR_E --> PG

    BOQ_P --> COMP_I
    COMP_I --> WIN_P
    WIN_P --> BID_O
    BID_O --> EXEC_D

    PG --> API_R
    PG --> EXCEL
    PG --> DASH
    EXEC_D --> NOTIFY
```

## Data Pipelines

| Pipeline | Source → Processing → Storage | Frequency |
|----------|------------------------------|-----------|
| Tender Discovery | e-GP → TenderRadar → PostgreSQL | Daily |
| Document Acquisition | e-GP → Acquisition → FS + KB | On-demand |
| BOQ Comparison | Upload → PDFParser → BOQProcessor → PostgreSQL | On-demand |
| Rate Analysis | BOQ Items → RateEngine → PostgreSQL | On-demand |
| Material Prices | BD Sites → Crawler → market_index | Weekly |
| Intelligence | Multiple → Pipeline → Knowledge Lake | On-demand |

## Data Retention

| Data Type | Retention | Policy |
|-----------|-----------|--------|
| Tender records | Permanent | No deletion |
| Award records | Permanent | No deletion |
| BOQ comparisons | 1 year | Auto-archive |
| Uploaded files | 90 days | Auto-delete |
| Audit events | 7 years | Legal requirement |
| Agent jobs | 30 days | Auto-cleanup |
