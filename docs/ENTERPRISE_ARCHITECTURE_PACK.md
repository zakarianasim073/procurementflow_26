# Enterprise Architecture Pack — Master Index

> Complete enterprise architecture documentation for ProcureFlow BD.
> Generated: 2026-07-24. Last updated: 2026-07-24.

---

## Document Map

| Phase | Description | Count | Directory |
|-------|-------------|-------|-----------|
| **Phase A** | API Contracts | 20 docs | `docs/api/` |
| **Phase B** | Component Contracts | 80 specs | `docs/components/` |
| **Phase C** | Screen Specifications | 100 screens | `docs/screens/` |
| **Phase D** | Sequence Diagrams | 15 diagrams | `docs/sequences/` |
| **Phase E** | Architecture Diagrams | 10 diagrams | `docs/architecture/` |
| **Phase F** | Database ER Diagrams | 5 diagrams | `docs/database/` |
| **Phase G** | AI Agent Design | 10 docs (49 agents) | `docs/agents/` |
| **Phase H** | Event Contracts | 4 schemas (23 events) | `docs/events/` |
| **Phase I** | ADRs (021-030) | 10 ADRs | `docs/architecture/ADRs_021-030.md` |
| **Phase J** | Implementation Tickets | 105 tickets | `docs/IMPLEMENTATION_TICKETS.md` |

## Supporting Documents

| Document | Location |
|----------|----------|
| ADR Baseline (001-020) | `ADR_BASELINE.md` |
| Implementation Roadmap | `IMPLEMENTATION_ROADMAP.md` |
| Repository Map | `REPOSITORY_MAP.md` |
| Domain Baseline | `DOMAIN_BASELINE.md` |
| Architecture Baseline | `ARCHITECTURE_BASELINE.md` |

---

## Index Files

| Phase | Index |
|-------|-------|
| API Contracts | `docs/api/INDEX.md` |
| Component Contracts | `docs/components/INDEX.md` |
| Screen Specifications | `docs/screens/INDEX.md` |
| Sequence Diagrams | `docs/sequences/INDEX.md` |
| Architecture Diagrams | `docs/architecture/INDEX.md` |
| Database ER Diagrams | `docs/database/INDEX.md` |
| AI Agent Design | `docs/agents/INDEX.md` |
| Event Contracts | `docs/events/INDEX.md` |

---

## Quick Reference

### API Contracts (Phase A)
- `00_API_OVERVIEW.md` — Base URL, auth, error format, pagination
- `01_AUTH.md` — Registration, login, SSO, token refresh
- `02_BOQ.md` — Upload, compare, brain-compare, jobs
- `03_SOR.md` — Agencies, rates, search, match
- `04_TENDERS.md` — CRUD, search, lifecycle
- `05_AWARDS.md` — Awards, statistics
- `06_CONTRACTORS.md` — Profiles, capacity, DNA
- `07_PRICING.md` — Estimation, rate analysis
- `08_COMPETITORS.md` — Intelligence, leaderboard
- `09_INTELLIGENCE.md` — Market, agency, zone intel
- `10_AGENTS.md` — Execute, pipeline, status
- `11_REPORTS.md` — Generate, download
- `12_DASHBOARD.md` — Executive, tender dashboard
- `13_SEARCH.md` — Global, tender, award, contractor search
- `14_PPR2025.md` — Evaluate, compliance, SLT
- `15_ENTERPRISE.md` — Audit, webhooks, RBAC, quotas
- `16_SSO.md` — OIDC, SAML integration
- `17_ADMIN.md` — System management
- `18_CRAWLER.md` — Plugin management, jobs
- `19_WEBHOOKS.md` — Registration, delivery

### Sequence Diagrams (Phase D)
- `SEQ-001` — BOQ Upload & SOR Comparison
- `SEQ-002` — Brain-Based BOQ Comparison
- `SEQ-003` — Full Tender Acquisition Pipeline
- `SEQ-004` — Tender Radar Scanning (e-GP)
- `SEQ-005` — Intelligence Pipeline (Full Chain)
- `SEQ-006` — Bid/No-Bid Decision Engine
- `SEQ-007` — Rate Analysis with Market Comparison
- `SEQ-008` — PPR 2025 Evaluation & TEC Scoring
- `SEQ-009` — Contractor Intelligence & Capacity
- `SEQ-010` — Tender Qualification Scoring
- `SEQ-011` — Crawler Orchestration & Import
- `SEQ-012` — Multi-Agent Orchestrator (14 Phases)
- `SEQ-013` — Knowledge Brain Query & Storage
- `SEQ-014` — Executive Intelligence Report
- `SEQ-015` — Idle-Time Intelligence Cycle

### Architecture Diagrams (Phase E)
- `ARCH-001` — System Architecture Overview
- `ARCH-002` — Backend Component Architecture
- `ARCH-003` — Agent Architecture
- `ARCH-004` — Database Architecture
- `ARCH-005` — Frontend Component Architecture
- `ARCH-006` — API Gateway & Routing
- `ARCH-007` — Authentication & Authorization
- `ARCH-008` — Deployment Architecture
- `ARCH-009` — Data Flow Architecture
- `ARCH-010` — Integration Architecture

---

## Coverage Summary

| Domain | API | Components | Screens | Diagrams | Agents | Events |
|--------|-----|-----------|---------|----------|--------|--------|
| BOQ & Pricing | ✓ | ✓ | ✓ | SEQ-001,002,007 | 011,012 | — |
| Tender Discovery | ✓ | ✓ | ✓ | SEQ-003,004 | 001,002,003 | 8 events |
| Intelligence | ✓ | ✓ | ✓ | SEQ-005 | 005,006,014 | — |
| Evaluation | ✓ | ✓ | ✓ | SEQ-008,010 | 007,008,009,010 | — |
| Competitor | ✓ | ✓ | ✓ | SEQ-006 | 013,015,016,017 | — |
| Decision | ✓ | ✓ | ✓ | SEQ-006 | 018,021,022,039 | — |
| Knowledge | ✓ | ✓ | ✓ | SEQ-013 | 025,023 | 4 events |
| Enterprise | ✓ | ✓ | ✓ | ARCH-007 | — | 5 events |
| Agents | ✓ | ✓ | ✓ | SEQ-012 | all 49 | 6 events |
| Reporting | ✓ | ✓ | ✓ | SEQ-014 | 023 | — |
