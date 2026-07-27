# Database Audit Consolidation Notes

> Generated from the database audit report. These are tracking notes for future migrations, not immediate fixes.

## 1. Duplicate Contractor Tables

| Table | Location | Status | Notes |
|-------|----------|--------|-------|
| `contractors` | `app.db.models` | **Active** | Legacy but still used by agents. `contractor_name` is unique. |
| `contractor_dna` | `app.models.intelligence` | **Deprecated** | V1 DNA. Superseded by `contractor_dna_v2`. Migration 005 created v2 but did not migrate data. |
| `contractor_dna_v2` | `app.models.intelligence` | **Active** | Created in migration 005 with 20+ columns. Agents should migrate to this. |

**Recommended path:**
1. Write a one-time migration to backfill `contractor_dna_v2` from `contractor_dna` + `contractors`.
2. Update all agents to query `contractor_dna_v2` exclusively.
3. Drop `contractor_dna` (v1) in a subsequent migration.
4. Keep `contractors` as the human-readable name table; `contractor_dna_v2` as the analytics table.

## 2. Duplicate Tender Tables

| Table | Location | PK Type | Status | Notes |
|-------|----------|---------|--------|-------|
| `tenders` | `app.db.models` | `id` (UUID) + `tender_id` (String, unique) | **DEPRECATED** | Legacy schema. `tender_id` is the business key. Many FKs reference it. |
| `procurement_tenders` | `app.models.intelligence` | `id` (UUID); `package_no` is business key | **Canonical** | New code should use this. |
| `tender_data_pool` | `app.db.models` | `id` (UUID) | **Active** | Extracted BOQ, docs, criteria. Overlaps with `tenders.raw_data` JSON. |

**Recommended path:**
1. Do NOT drop `tenders` until all FK references (`agent_results`, `npp_records`, `knowledge_entries`) are migrated to `procurement_tenders` or decoupled.
2. Add `procurement_tender_id` (UUID) to `agent_results`, `npp_records`, and `knowledge_entries`.
3. Backfill from existing `tender_id` → `package_no` → `procurement_tenders.id` mapping.
4. Once all consumers use `procurement_tenders`, drop `tenders` and its dependent FKs.

## 3. Duplicate Award Tables

| Table | Status | Notes |
|-------|--------|-------|
| `award_records` | **Unused** | Legacy. No agents reference it. Safe to drop after confirming no ETL scripts use it. |
| `award_records_v2` | **Canonical** | All agents use this. Migration 006 adds FK to `procurement_tenders`. |

**Recommended path:**
1. Search for any remaining `award_records` references in ETL scripts.
2. If none found, drop `award_records` in a migration.

## 4. Experience Tables (eexperience_completed / ecms_ongoing)

These tables are ~95% column-identical. The runtime `ALTER TABLE` blocks in `intelligence_data_service.py` add the same columns to both.

**Recommended path:**
1. Merge into a single `contractor_experience` table with a `data_source` column discriminator.
2. Partition by `data_source` if query patterns differ significantly.

## 5. Schema Drift from Runtime DDL

The following runtime DDL exists and should be captured in Alembic:

- `intelligence_data_service._ensure_eexperience_schema()` — adds 13+ columns to `econtract_execution`, 15+ columns to `eexperience_completed`/`ecms_ongoing`
- `intelligence_data_service._ensure_award_schema()` — adds 10 columns to `award_records_v2`
- `intelligence_data_service.backfill_tender_regimes()` — adds `regime` column to `tenders`

**Recommended path:**
1. Inspect production DB to get actual column lists.
2. Create a migration (007+) that captures all these columns with `IF NOT EXISTS` guards.
3. Once the migration covers all columns, the runtime methods can become no-ops.

## 6. Async Migration of Agents

Agents still using `get_sync_engine()` inside `async def execute()`:

- `win_probability.py` — partially fixed via `db_helpers`; `_score_knowledge_graph` still uses sync engine for agency/zone queries
- `bid_position_optimizer.py` — fully fixed via `db_helpers`
- `eligibility_compliance.py` — still uses sync engine for contractor lookups
- `competitor_intelligence.py` — fully fixed via `db_helpers`
- `risk_intelligence.py` — still uses sync engine if DB queries are added

**Recommended path:**
1. Migrate all agent DB access to async session helpers.
2. Use `asyncio.to_thread()` only for heavy analytical code that cannot be rewritten.

## 7. Missing Foreign Keys (Future)

These FKs were intentionally skipped in migration 006 because they reference the deprecated `tenders` table:

- `npp_records.tender_id` → `tenders.tender_id` (added in 006, but target is deprecated)
- `agent_results.tender_id` → `tenders.tender_id` (added in 006, but target is deprecated)

Once `tenders` is replaced by `procurement_tenders`, these FKs should be updated to point to the canonical table.

## Migration Checklist

- [ ] 006: Add missing indexes + FKs (done)
- [ ] 007: Capture runtime DDL from `intelligence_data_service.py`
- [ ] 008: Backfill `contractor_dna_v2` from `contractor_dna`
- [ ] 009: Drop `award_records` (legacy)
- [ ] 010: Add `procurement_tender_id` to `agent_results`, `npp_records`, `knowledge_entries`
- [ ] 011: Backfill `procurement_tender_id` from `tender_id` mappings
- [ ] 012: Drop `contractor_dna` (v1)
- [ ] 013: Drop `tenders` after all consumers migrated
- [ ] 014: Merge `eexperience_completed` + `ecms_ongoing`
