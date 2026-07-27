# SEQ-011: Crawler Orchestration & Data Import

```mermaid
sequenceDiagram
    autonumber
    actor User as Admin User
    participant API as POST /api/crawler/run
    participant Orch as CrawlerOrchestrator
    participant Queue as TaskQueue
    participant Plugin as Crawler Plugin
    participant Import as CrawlImportService
    participant Match as TenderMatchingService
    participant DB as PostgreSQL

    User->>API: POST /api/crawler/run { plugin: "bwdb_tenders" }
    API->>Orch: enqueue(plugin, priority=HIGH)

    rect rgb(240, 248, 255)
        Note over Orch,Plugin: Phase 1: Plugin Execution
        Orch->>Queue: dequeue_next()
        Queue-->>Orch: Task(plugin, params)
        Orch->>Plugin: Plugin.run(params)
        Plugin->>Plugin: Crawl target data source
        Plugin-->>Orch: RawResult[] { items: [...], metadata: {...} }
    end

    rect rgb(240, 255, 240)
        Note over Orch,Import: Phase 2: Validation & Dedup
        Orch->>Orch: Validate schema (required fields)
        Orch->>DB: SELECT existing IDs
        Orch->>Orch: Deduplicate against existing
    end

    rect rgb(255, 248, 240)
        Note over Orch,Import: Phase 3: Import
        Orch->>Import: import_tenders(validated_items)
        Import->>DB: INSERT INTO procurement_tenders (batch)
        Import->>DB: INSERT INTO procurement_lifecycle
        opt APP Records
            Import->>DB: INSERT INTO app_records
        end
        opt Awards
            Import->>DB: INSERT INTO procurement_awards
        end
        Import-->>Orch: { imported: 25, skipped: 3 }
    end

    rect rgb(248, 240, 255)
        Note over Orch,Match: Phase 4: Lifecycle Rebuild
        Orch->>Match: rebuild_lifecycle(new_tender_ids)
        Match->>DB: Match tenders to awards by package_no + agency
        Match->>DB: UPDATE procurement_lifecycle SET award_id = ...
        Match-->>Orch: { matched: 20 }
    end

    Orch->>DB: Update task status (completed)
    Orch-->>API: { imported: 25, matched: 20 }
```

## Plugin Types

| Plugin | Source | Frequency |
|--------|--------|-----------|
| bwdb_tenders | BWDB website | Daily |
| lged_tenders | LGED portal | Daily |
| pwd_tenders | PWD website | Daily |
| rhd_tenders | RHD website | Weekly |
| material_prices | BD seller sites | Weekly |

## Error Paths

1. **Plugin timeout** — Task marked FAILED after 5min, retry 2x
2. **Import conflict** — Duplicate tender_id → skip, log
3. **Schema validation** — Invalid item → reject, log to error queue
