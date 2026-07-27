# ARCH-004: Database Architecture

```mermaid
graph TB
    subgraph "PostgreSQL 17 (Port 5433)"
        subgraph "Tender Domain"
            T1[procurement_tenders<br/>395K rows]
            T2[procurement_lifecycle]
            T3[app_records<br/>207K rows]
            T4[boq_items]
            T5[boq_comparisons]
            T6[boq_jobs]
        end

        subgraph "Award Domain"
            A1[procurement_awards<br/>238K rows]
            A2[award_records_v2]
        end

        subgraph "Contractor Domain"
            C1[contractors<br/>32K rows]
            C2[contractor_dna]
            C3[contractor_capacity]
            C4[contractor_finance]
            C5[canonical_contractors]
            C6[canonical_contractor_aliases]
        end

        subgraph "SOR Domain"
            S1[sor_rates<br/>4545 rows]
            S2[sor_rates_archive]
        end

        subgraph "Knowledge Domain"
            K1[knowledge_entries<br/>21 columns]
            K2[knowledge_graph_nodes]
            K3[knowledge_graph_edges]
        end

        subgraph "Evaluation Domain"
            E1[ppr_evaluations]
            E2[tender_qualification_scores]
            E3[item_margins]
        end

        subgraph "Market Domain"
            M1[market_index<br/>material prices]
            M2[npp_trends]
        end

        subgraph "Enterprise Domain"
            EN1[users]
            EN2[audit_events]
            EN3[rbac_roles]
            EN4[rbac_permissions]
            EN5[webhook_registrations]
            EN6[retention_policies]
        end

        subgraph "Agent Domain"
            AG1[agent_jobs]
            AG2[thought_signatures]
        end
    end

    subgraph "Redis"
        R1[Session Cache]
        R2[Distributed Locks]
        R3[Rate Limiter]
        R4[Agent Memory Cache]
    end

    subgraph "File Storage"
        F1[uploads/]
        F2[tender_docs/]
        F3[reports/]
    end
```

## Table Sizes

| Table | Rows | Indexes |
|-------|------|---------|
| procurement_tenders | 395K | tender_id (PK), agency_code, closing_date |
| procurement_awards | 238K | contractor, agency, year |
| app_records | 207K | tender_id, package_no |
| contractors | 32K | canonical_id, name |
| sor_rates | 4,545 | agency+code (composite), description (GIN) |
| knowledge_entries | Variable | entry_type+tender_id, agent_id, tsvector |

## Key Relationships

```
procurement_tenders.tender_id → procurement_lifecycle.tender_id
procurement_tenders.tender_id → boq_items.tender_id
procurement_awards.tender_id → procurement_tenders.tender_id
contractors.canonical_id → contractor_dna.contractor_id
contractors.canonical_id → award_records_v2.contractor
sor_rates.code → boq_items.sor_code
```
