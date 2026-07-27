# ER-004: Knowledge & Agent Domain

```mermaid
erDiagram
    knowledge_entries {
        serial id PK
        varchar entry_type "tender_document/boq_text/tds_text/pipeline_result/bid_decision/rate_analysis/competitor_profile"
        varchar tender_id FK
        varchar agent_id
        jsonb data
        text summary
        text[] tags
        text source
        timestamp created_at
    }

    knowledge_graph_nodes {
        varchar entity_id PK
        varchar entity_type "tender/award/contractor/agency"
        jsonb properties
        timestamp created_at
    }

    knowledge_graph_edges {
        serial id PK
        varchar source_id FK
        varchar target_id FK
        varchar relationship_type "awarded_to/competes_with/belongs_to/similar_to"
        jsonb properties
        timestamp created_at
    }

    agent_jobs {
        uuid id PK
        varchar agent_id
        jsonb input
        jsonb output
        varchar status "running/completed/failed"
        text error_message
        timestamp started_at
        timestamp completed_at
    }

    thought_signatures {
        uuid id PK
        varchar agent_id
        varchar tender_id FK
        text thought_type
        jsonb thought_data
        jsonb signature
        varchar status "pending/approved/rejected"
        varchar approved_by
        timestamp created_at
        timestamp resolved_at
    }

    ppr_evaluations {
        serial id PK
        varchar tender_id FK
        varchar regime "PPR2008/PPR2025"
        jsonb evaluations "per-bid scores"
        jsonb lert_prediction
        jsonb ml_prediction
        numeric confidence
        timestamp created_at
    }

    knowledge_entries ||--o{ thought_signatures : "may trigger thought"
    knowledge_graph_nodes ||--o{ knowledge_graph_edges : "as source"
    knowledge_graph_nodes ||--o{ knowledge_graph_edges : "as target"
    procurement_tenders ||--o{ knowledge_entries : "has knowledge"
    procurement_tenders ||--o{ ppr_evaluations : "has evaluation"
```

## Knowledge Entry Types

| entry_type | Content | Stored By | Size Limit |
|------------|---------|-----------|------------|
| `tender_document` | Acquisition metadata + file paths | agent-002 | ~5KB |
| `boq_text` | Extracted BOQ PDF text | agent-002 | 50KB |
| `tds_text` | Extracted TDS PDF text | agent-002 | 50KB |
| `pipeline_result` | Pipeline completion summary | agent-027 | ~10KB |
| `bid_decision` | Bid/No-Bid rationale | agent-039 | ~5KB |
| `rate_analysis` | Item cost breakdowns | agent-011 | ~20KB |
| `competitor_profile` | Competitor intelligence | agent-013 | ~10KB |

## Knowledge Graph Relationships

```
TENDER --awarded_to--> CONTRACTOR
TENDER --belongs_to--> AGENCY
TENDER --similar_to--> TENDER
CONTRACTOR --competes_with--> CONTRACTOR
AWARD --awards_tender--> TENDER
```
