# SEQ-002: Brain-Based BOQ Comparison

```mermaid
sequenceDiagram
    autonumber
    actor User as Frontend User
    participant API as POST /api/boq/brain-compare
    participant Brain as AgentBrain
    participant KB as Knowledge Entries (DB)
    participant PDF as PDFParser
    participant TDS as TDSExtractor
    participant BOQ as BOQProcessor
    participant SOR as SOR Service
    participant APP as app_records (DB)
    participant DB as PostgreSQL

    User->>API: POST /api/boq/brain-compare { tender_id, sor_agency, zone }
    API->>Brain: query_brain("boq_text", tender_id)
    Brain->>KB: SELECT * FROM knowledge_entries WHERE entry_type='boq_text' AND tender_id=$1
    KB-->>Brain: boq_text entry (up to 50K chars)

    API->>Brain: query_brain("tds_text", tender_id)
    Brain->>KB: SELECT * FROM knowledge_entries WHERE entry_type='tds_text' AND tender_id=$1
    KB-->>Brain: tds_text entry

    API->>PDF: pdfplumber.extract(boq_text)
    PDF-->>API: Parsed BOQ items[]

    API->>TDS: extract_tds_criteria(tds_text)
    Note over TDS: Regex parsing e-GP bracket format<br/>[50,00,000] → 5000000
    TDS-->>API: { experience, turnover, liquid_assets, tender_capacity, ... }

    API->>APP: SELECT estimate_amount FROM app_records WHERE tender_id=$1
    APP-->>API: APP estimate (if available)

    API->>BOQ: BOQProcessor.compare(items, agency, zone)
    loop For each BOQ item
        BOQ->>SOR: find_rate(code, desc, agency, zone)
        SOR-->>BOQ: Match result
    end
    BOQ-->>API: ComparisonResult[]

    API->>DB: Persist Tender + BOQItem + BOQComparison
    API-->>User: { comparison[], tds_criteria, app_estimate }
```

## Participants

| Actor/Component | Type | Description |
|----------------|------|-------------|
| Frontend User | Actor | Browser SPA requesting brain comparison |
| AgentBrain | Agent Core | Central knowledge store + query engine |
| Knowledge Entries | DB | PostgreSQL table storing extracted texts |
| PDFParser | Service | BOQ text extraction from stored content |
| TDSExtractor | Service | Regex-based TDS financial criteria parsing |
| BOQProcessor | Service | SOR matching engine |
| SOR Service | Service | In-memory rate lookup |
| app_records | DB | APP plan records for estimate lookup |

## Key Differences from SEQ-001

- No file upload required — uses pre-acquired tender documents
- TDS criteria extraction included (7 financial fields)
- APP estimate lookup for context
- Relies on agent-002 having previously acquired documents

## Error Paths

1. **No knowledge entry found** — Brain returns empty → API returns 404 "Tender not acquired"
2. **BOQ text too large** — Truncated at 50K chars → partial extraction warning
3. **TDS parse failure** — Empty criteria returned with warning flags
