# ER-002: Contractor & DNA Domain

```mermaid
erDiagram
    contractors {
        serial id PK
        varchar canonical_id FK
        text name
        text bin_number
        text contact_info
        timestamp created_at
    }

    canonical_contractors {
        varchar canonical_id PK
        text official_name
        text bin_number
        text registration_status
        timestamp created_at
    }

    canonical_contractor_aliases {
        serial id PK
        varchar canonical_id FK
        text alias
        text source
    }

    contractor_dna {
        serial id PK
        varchar contractor_id FK "canonical_id"
        numeric execution_score
        numeric reliability_score
        numeric completion_rate
        numeric on_time_rate
        numeric avg_delay_days
        integer total_projects
        numeric avg_award_value
        timestamp computed_at
    }

    contractor_capacity {
        serial id PK
        varchar contractor_id FK "canonical_id"
        integer concurrent_projects
        integer max_concurrent "default 8"
        numeric current_workload
        numeric available_capacity
        timestamp computed_at
    }

    contractor_finance {
        serial id PK
        varchar contractor_id FK "canonical_id"
        numeric annual_turnover
        numeric running_contracts_value
        numeric pending_bids_value
        numeric leverage_ratio
        text risk_level "LOW/MODERATE/HIGH"
        timestamp computed_at
    }

    contractor_profile_complete {
        text name
        varchar canonical_id
        integer total_projects
        numeric completion_rate
        numeric on_time_rate
        numeric execution_score
        numeric reliability_score
        integer concurrent_projects
        numeric annual_turnover
        text risk_level
    }

    canonical_contractors ||--o{ contractors : "has aliases"
    canonical_contractors ||--o| contractor_dna : "has DNA"
    canonical_contractors ||--o| contractor_capacity : "has capacity"
    canonical_contractors ||--o| contractor_finance : "has finance"
    canonical_contractors ||--o{ canonical_contractor_aliases : "has aliases"
    contractors }o--|| canonical_contractors : "canonical mapping"
```

## DNA Score Computation

```
execution_score = (completion_rate × 40 + on_time_rate × 30 + reliability × 30) / 100
reliability_score = f(avg_delay_days, on_time_rate)
leverage_ratio = (running_contracts + pending_bids) / annual_turnover
```

## Capacity Metrics

| Metric | Formula | Alert Threshold |
|--------|---------|----------------|
| Utilization | concurrent / max_concurrent | > 0.85 |
| Available | max - concurrent | < 1 |
| Workload Ratio | current_workload / available | > 0.9 |
