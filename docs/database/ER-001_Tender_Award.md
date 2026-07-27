# ER-001: Tender & Award Domain

```mermaid
erDiagram
    procurement_tenders {
        varchar tender_id PK
        text title
        varchar agency_code
        varchar package_no
        numeric estimated_amount
        date closing_date
        text category "Works only"
        varchar zone
        text status
        timestamp created_at
    }

    procurement_lifecycle {
        serial id PK
        varchar tender_id FK
        varchar award_id FK
        text status "active/won/lost/cancelled"
        timestamp updated_at
    }

    app_records {
        serial id PK
        varchar tender_id FK
        varchar package_no
        text description
        numeric estimated_amount
        varchar agency_code
        text fiscal_year
        date publish_date
    }

    procurement_awards {
        serial id PK
        varchar tender_id FK
        text contractor_name
        numeric award_amount
        numeric discount_pct
        date award_date
        varchar agency_code
        text zone
    }

    award_records_v2 {
        serial id PK
        varchar tender_id FK
        text contractor
        numeric value
        numeric discount_pct
        varchar agency
        integer year
        text zone
        text work_type
    }

    boq_items {
        serial id PK
        varchar tender_id FK
        varchar item_code
        text description
        varchar unit
        numeric quantity
        numeric sor_rate
        numeric quoted_rate
        numeric diff
        numeric pct_diff
        text flag
    }

    boq_comparisons {
        serial id PK
        varchar tender_id FK
        varchar sor_agency
        varchar zone
        jsonb tender_info
        numeric total_sor
        numeric total_quoted
        numeric total_diff
        timestamp created_at
    }

    boq_jobs {
        uuid id PK
        varchar status "processing/completed/failed"
        text error_message
        timestamp created_at
        timestamp completed_at
    }

    tender_qualification_scores {
        serial id PK
        varchar tender_id FK
        varchar contractor_id FK
        numeric composite_score
        text recommendation
        jsonb breakdown
        jsonb risk_factors
        timestamp created_at
    }

    procurement_tenders ||--o{ procurement_lifecycle : "has lifecycle"
    procurement_tenders ||--o{ boq_items : "has boq items"
    procurement_tenders ||--o{ boq_comparisons : "has comparisons"
    procurement_tenders ||--o{ procurement_awards : "may be awarded"
    procurement_tenders ||--o{ app_records : "may have APP record"
    procurement_tenders ||--o{ tender_qualification_scores : "qualification"
    procurement_lifecycle }o--|| procurement_awards : "links to award"
    procurement_awards }o--|| procurement_tenders : "awards tender"
    award_records_v2 }o--|| procurement_tenders : "award of tender"
    boq_items }o--|| boq_comparisons : "belongs to comparison"
```

## Key Indexes

| Table | Index | Columns |
|-------|-------|---------|
| procurement_tenders | PK | tender_id |
| procurement_tenders | idx_agency | agency_code |
| procurement_tenders | idx_closing | closing_date |
| procurement_awards | idx_contractor | contractor_name |
| award_records_v2 | idx_contractor | contractor |
| award_records_v2 | idx_agency_year | agency, year |
| boq_items | idx_tender | tender_id |
