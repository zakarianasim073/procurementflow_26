# SEQ-015: Idle-Time Intelligence Cycle

```mermaid
sequenceDiagram
    autonumber
    participant API as POST /api/brain/idle-cycle
    participant Brain as AgentBrain
    participant A038 as TenderPreScreener (038)
    participant A001 as TenderRadar (001)
    participant A014 as AwardIntelligence (014)
    participant A013 as CompetitorIntel (013)
    participant A044 as SORZoneMatcher (044)
    participant A048 as MaterialPriceCrawler (048)
    participant A049 as MaterialMarginAnalyzer (049)
    participant DB as PostgreSQL

    API->>Brain: idle_cycle()

    rect rgb(240, 248, 255)
        Note over Brain,A038: P1: Fill Empty Tables
        Brain->>A038: execute({ action: "fill_empty_tables" })
        A038->>DB: SELECT tender_id FROM procurement_tenders WHERE boq_items_count=0
        DB-->>A038: unprocessed tenders
        loop For each tender
            A038->>DB: INSERT INTO boq_items (parsed items)
            A038->>DB: INSERT INTO tender_documents (metadata)
        end
        A038-->>Brain: { filled: 15 }
    end

    rect rgb(240, 255, 240)
        Note over Brain,A001: P1: Scan New Tenders
        Brain->>A001: execute({ action: "scan_live_tenders" })
        A001->>DB: INSERT INTO procurement_tenders (new tenders)
        A001-->>Brain: { new: 8 }
    end

    rect rgb(255, 248, 240)
        Note over Brain,A014: P2: Enrich Award-NPP Links
        Brain->>A014: execute({ action: "enrich_awards" })
        A014->>DB: SELECT awards WHERE npp_index IS NULL
        DB-->>A014: unlinked awards
        A014->>DB: UPDATE award_records_v2 SET npp_index = ...
        A014-->>Brain: { enriched: 120 }
    end

    rect rgb(248, 240, 255)
        Note over Brain,A013: P2: Update Competitor Profiles
        Brain->>A013: execute({ action: "update_profiles" })
        A013->>DB: SELECT contractor, COUNT(*), SUM(value) FROM award_records_v2 GROUP BY contractor
        DB-->>A013: award aggregations
        A013->>DB: UPSERT INTO contractor_dna (scores, metrics)
        A013-->>Brain: { updated: 45 }
    end

    rect rgb(255, 240, 240)
        Note over Brain,A044: P2: Map Districts to SOR Zones
        Brain->>A044: execute({ action: "map_zones" })
        A044->>DB: SELECT DISTINCT district FROM procurement_tenders WHERE sor_zone IS NULL
        DB-->>A044: unmapped districts
        A044->>DB: UPDATE procurement_tenders SET sor_zone = ...
        A044-->>Brain: { mapped: 30 }
    end

    rect rgb(240, 255, 248)
        Note over Brain,A048: P3: Crawl Material Prices
        Brain->>A048: execute({ action: "crawl_prices" })
        A048->>A048: Crawl BD construction material websites
        A048->>DB: UPSERT INTO market_index (material, price, date)
        A048-->>Brain: { materials_updated: 25 }
    end

    rect rgb(255, 255, 240)
        Note over Brain,A049: P3: Compute Profit Margins
        Brain->>A049: execute({ action: "compute_margins" })
        A049->>DB: SELECT sor_code, sor_rate FROM sor_rates
        A049->>DB: SELECT material, price FROM market_index
        A049->>A049: margin = (sor_rate - market_cost) / market_cost × 100
        A049->>DB: UPSERT INTO item_margins (code, margin_pct)
        A049-->>Brain: { margins_computed: 150 }
    end

    Brain->>Brain: broadcast("idle_cycle_complete")
    Brain-->>API: { status: "completed", tasks: 7, duration: "120s" }
```

## Idle Cycle Priority Tiers

| Priority | Agents | Purpose | Frequency |
|----------|--------|---------|-----------|
| P1 | 038, 001 | Fill gaps + discover | Every idle cycle |
| P2 | 014, 013, 044 | Enrich existing data | Every idle cycle |
| P3 | 048, 049 | Predictive pre-computation | Every 2nd cycle |
| P4 | 025 | Knowledge lake backfill | Weekly |

## Timing

| Phase | Duration |
|-------|----------|
| P1: Fill + Scan | 30-60s |
| P2: Enrich | 20-40s |
| P3: Crawl + Compute | 40-80s |
| **Total** | **90-180s** |
