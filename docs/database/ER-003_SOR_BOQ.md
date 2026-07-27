# ER-003: SOR & BOQ Domain

```mermaid
erDiagram
    sor_rates {
        serial id PK
        varchar agency "BWDB/PWD/LGED"
        varchar code "item code"
        text description
        varchar unit
        numeric zone_a
        numeric zone_b
        numeric zone_c
        numeric zone_d
        timestamp updated_at
    }

    sor_rates_archive {
        serial id PK
        varchar agency
        varchar code
        text description
        varchar unit
        numeric zone_a
        numeric zone_b
        numeric zone_c
        numeric zone_d
        date archived_at
    }

    market_index {
        serial id PK
        text material_name
        numeric price_per_unit
        varchar unit
        text source
        date recorded_at
        timestamp created_at
    }

    item_margins {
        serial id PK
        varchar sor_code FK
        varchar agency
        numeric sor_rate
        numeric market_cost
        numeric margin_pct
        timestamp computed_at
    }

    rate_analysis_templates {
        serial id PK
        varchar sor_code FK
        jsonb composition "material/labor/equipment breakdown"
        timestamp updated_at
    }

    npp_trends {
        serial id PK
        varchar agency
        varchar zone
        numeric npp_index
        date period
        timestamp created_at
    }

    sor_rates ||--o{ item_margins : "has margin analysis"
    sor_rates ||--o| rate_analysis_templates : "has composition"
```

## SOR Code Patterns (Agency Detection)

| Agency | Pattern | Regex | Example |
|--------|---------|-------|---------|
| BWDB | `XX-XXX-XX` (dash-separated) | `^\d{2}-\d{3}-\d{2}` | `40-200-00` |
| PWD | `XX.XX...` (dotted, 2-digit prefix) | `^\d{2}\.\d` | `26.50.1` |
| LGED | `X.XX.XX...` (dotted, 1-digit prefix) | `^[2-9]\.\d{2}` | `4.09.01.01` |

## Zone Mapping (Division → Zone)

| Division | BWDB/PWD | LGED |
|----------|----------|------|
| Dhaka, Mymensingh | A | A |
| Chattogram, Sylhet | B | B |
| Khulna, Barishal | **C** | **D** |
| Rajshahi, Rangpur | **D** | **C** |
