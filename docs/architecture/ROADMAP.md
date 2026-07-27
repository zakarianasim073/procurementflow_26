# ROADMAP.md – ProcureFlow Enterprise Execution Guide

This roadmap ties Phase 9–10 audit items to the AI workflows and prompt IDs in `WORKFLOWS.md` and `PROMPTS.md`.

Use it as the daily guide for moving ProcureFlow BD from current state to production-ready (P0), enterprise-ready (P1), and scale-ready (P2).

---

## 0. How to Use This Roadmap

For each roadmap item:

1. **Understand context**
   - Use Architecture + Audit prompts (Section 2 of PROMPTS.md).

2. **Plan**
   - Use 3.2 Feature Ticket and 21 Architecture Decision Validation prompts.

3. **Implement**
   - Use the appropriate 4.x Implementation Plan + Code prompts.

4. **Review & Harden**
   - Use 22 Code Review, 23 Enterprise Testing, and Release Readiness prompts.

Always obey the Global Constraints, Assumption Check, Context Budget, and Standard Output Contract from `WORKFLOWS.md`.

---

## 1. P0 – 30-Day Production Hardening

Based on Phase 10 “30-Day Plan (P0 — Must Fix Before Production)”.[file:24]

### P0-01 Add Missing DB Indexes on `award_records_v2`

- Source: Phase 10 P0 list, Production Risk #1 (full table scan).[file:24]
- Area: Database, performance.
- Prompts:
  - Context & audit: 2.3 Database & RLS Audit.
  - Ticket: 3.2 Feature Ticket.
  - Architecture validation: 21 Architecture Decision Validation.
  - Design: 4.2 DB & Migration Implementation – Plan.
  - Code: 4.2 DB & Migration Implementation – Code.
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (DB + performance smoke).
- Status: TODO / IN PROGRESS / DONE

---

### P0-02 Set Up PgBouncer Connection Pooling

- Source: Phase 10 P0 list, Production Risk #8 (no connection pooling).[file:24]
- Area: Database, infra.
- Prompts:
  - Context: 2.7 Performance Audit.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.2 DB & Migration Implementation – Plan.
  - Code (DB config integration, health checks): 4.2 DB & Migration Implementation – Code.
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (connection pool behaviour, RLS unaffected).
- Status: TODO / IN PROGRESS / DONE

---

### P0-03 Add Rate Limiting Middleware

- Source: Phase 10 P0 list, Production Risk #3 (no rate limiting).[file:24]
- Area: Backend API.
- Prompts:
  - Context: 2.2 Backend Architecture Audit, 2.6 Security Audit, 2.7 Performance Audit.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.1 Backend Implementation – Plan.
  - Code: 4.1 Backend Implementation – Code (ratelimiter integration, per-tenant if possible).
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (security, perf, async).
- Status: TODO / IN PROGRESS / DONE

---

### P0-04 Implement `/health`, `/ready`, `/live` Endpoints

- Source: Phase 10 P0 list, Missing Health checks (Top 30 features #9, production risk #11).[file:24]
- Area: Backend, operations.
- Prompts:
  - Context: 2.2 Backend Architecture Audit, integration-workflows health sections.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.1 Backend Implementation – Plan.
  - Code: 4.1 Backend Implementation – Code.
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (K8s probe behaviour, agent/DB status).
- Status: TODO / IN PROGRESS / DONE

---

### P0-05 Configure PostgreSQL WAL Archiving + PITR

- Source: Phase 10 P0 list, Production Risks #19 (missing PITR).[file:24]
- Area: Database, DR.
- Prompts:
  - Context: 2.3 Database & RLS Audit.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.2 DB & Migration Implementation – Plan.
  - Code/config: 4.2 DB & Migration Implementation – Code (PG settings, backup scripts).
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (DR drill tests in TESTING_GUIDE).
- Status: TODO / IN PROGRESS / DONE

---

### P0-06 Add File Upload Validation (Size, Type, Virus Scan)

- Source: Phase 10 P0 list, Missing Feature #24 / Production Risk #6.[file:24]
- Area: Backend, security.
- Prompts:
  - Context: 2.6 Security Audit, 2.4 Integration Audit (MinIO, uploads).
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.1 Backend Implementation – Plan.
  - Code: 4.1 Backend Implementation – Code (upload middleware, virus scanning integration).
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (security, integration, perf).
- Status: TODO / IN PROGRESS / DONE

---

### P0-07 Set Up Structured JSON Logging

- Source: Phase 10 P0 list, Missing Feature #10.[file:24]
- Area: Backend, observability.
- Prompts:
  - Context: 2.2 Backend Architecture Audit, 2.7 Performance Audit.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.1 Backend Implementation – Plan.
  - Code: 4.1 Backend Implementation – Code (logging config, structured logs).
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (log presence/format in key paths).
- Status: TODO / IN PROGRESS / DONE

---

### P0-08 Add Request Correlation IDs

- Source: Phase 10 P0 list, Production Risk #15 (no request ID tracing).[file:24]
- Area: Backend, observability.
- Prompts:
  - Context: 2.2 Backend Architecture Audit.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.1 Backend Implementation – Plan.
  - Code: 4.1 Backend Implementation – Code (middleware, log integration).
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (correlation IDs across API, agents, crawlers).
- Status: TODO / IN PROGRESS / DONE

---

### P0-09 Implement JWT Refresh Token Flow

- Source: Phase 10 P0 list, Production Risk #5 (no refresh).[file:24]
- Area: Backend security.
- Prompts:
  - Context: 2.6 Security Audit, 2.2 Backend Architecture Audit.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.1 Backend Implementation – Plan.
  - Code: 4.1 Backend Implementation – Code (auth routes, token model, DB changes if needed).
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (security, regression).
- Status: TODO / IN PROGRESS / DONE

---

### P0-10 Containerize All Services (Dockerfile Audit)

- Source: Phase 10 P0 list (containerization).[file:24]
- Area: DevOps.
- Prompts:
  - Context: 2.2 Backend Architecture Audit, overview deployment sections.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: DevOps implementation plan (you can create a DevOps-specific plan prompt if needed).
  - Code/config: 4.4 Integration & Webhook Implementation – Code (for runtime scripts) + infra changes outside model if required.
  - Review: 22 Code Review (Dockerfiles, entrypoints).
  - Testing: 23 Enterprise Testing (basic container smoke tests).
- Status: TODO / IN PROGRESS / DONE

---

### P0-11 Set Up Prometheus + Grafana (Basic Metrics)

- Source: Phase 10 P0 list.[file:24]
- Area: Observability.
- Prompts:
  - Context: overview.md monitoring sections, complete-review telemetry parts.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.4 Integration Implementation – Plan (metrics export).
  - Code: 4.4 Integration Implementation – Code (metrics endpoints, instrumentation).
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (metrics presence, dashboards).
- Status: TODO / IN PROGRESS / DONE

---

### P0-12 Parameterize All Raw SQL Queries

- Source: Phase 10 P0 list, Production Risk #7 (SQL injection).[file:24]
- Area: Backend, DB security.
- Prompts:
  - Context: 2.3 Database & RLS Audit, 2.6 Security Audit.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.1/4.2 Implementation – Plan (depending on layer).
  - Code: 4.1 Backend Implementation – Code and/or 4.2 DB Implementation – Code.
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (security, regression).
- Status: TODO / IN PROGRESS / DONE

---

### P0-13 Set Up Automated Daily DB Backups

- Source: Phase 10 P0 list.[file:24]
- Area: DB/ops.
- Prompts:
  - Context: 2.3 Database & RLS Audit.
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.2 DB Implementation – Plan.
  - Code/config: 4.2 DB Implementation – Code (backup scripts, cron/K8s jobs).
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (backup + restore tests).
- Status: TODO / IN PROGRESS / DONE

---

### P0-14 Add Agent Execution Timeouts + Max Iterations

- Source: Phase 10 P0 list, Production Risk #16 (agent infinite loop).[file:24]
- Area: AgentBrain & agents.
- Prompts:
  - Context: 2.5 Agent & Brain Audit (iteration bug, circuit breakers).
  - Ticket: 3.2 Feature Ticket.
  - Validation: 21 Architecture Decision Validation.
  - Design: 4.3 Agent & Brain Implementation – Plan.
  - Code: 4.3 Agent & Brain Implementation – Code.
  - Review: 22 Code Review.
  - Testing: 23 Enterprise Testing (async, perf, regression).
- Status: TODO / IN PROGRESS / DONE

---

### P0-15 Create Deployment Runbook (One-pager)

- Source: Phase 10 P0 list.[file:24]
- Area: Operations.
- Prompts:
  - Context: overview.md deployment sections, OPERATIONS.md skeleton.
  - Ticket: 3.2 Feature Ticket (runbook).
  - Validation: 21 Architecture Decision Validation (for process changes).
  - Design-only: Documentation Update Prompt (5.3) to produce runbook text.
  - Review: 22 Code Review (if any scripts).
  - Testing: 23 Enterprise Testing (verify runbook steps as part of Release Readiness).
- Status: TODO / IN PROGRESS / DONE

---

## 2. P1 – 90-Day Enterprise Readiness

Summaries only; you can expand items similarly when you start them.[file:24]

### P1 Areas and Prompt Mapping

- **Multi-tenancy (Org isolation, schema-per-tenant, tenant middleware)**
  - Context: 2.3 DB & RLS Audit, ADR-020.
  - Prompts: 3.2 Feature Ticket, 21 Architecture Validation, 4.2 DB Implementation (Plan+Code), 22, 23.

- **Auth & RBAC (SSO/SAML/OIDC, granular permissions)**
  - Context: 2.6 Security Audit, 2.2 Backend Audit.
  - Prompts: 3.2, 21, 4.1 Backend (Plan+Code), 22, 23.

- **Testing (unit/integration/load)**
  - Context: complete-review tests section.
  - Prompts: 3.2, 23 Enterprise Testing, TESTING_GUIDE.md, Release Readiness.

- **CI/CD (GitHub Actions)**
  - Context: OPERATIONS.md, DevOps practices.
  - Prompts: 3.2, 21, Documentation Update, Release Readiness.

- **Database (slow query monitoring, index tuning, read replicas)**
  - Context: 2.3 DB Audit, 2.7 Performance.
  - Prompts: 3.2, 21, 4.2 DB Implementation, 22, 23.

- **Monitoring (Loki, Tempo, alert rules)**
  - Context: overview.md, COMPLETE REVIEW observability.
  - Prompts: 3.2, 21, 4.4 Integration Implementation, 5.4 Release Readiness.

- **API (versioning, webhook system)**
  - Context: 2.2 Backend Audit, 2.4 Integration Audit.
  - Prompts: 3.2, 21, 4.1 Backend Implementation, 4.4 Integration Implementation, 22, 23.

- **DevOps (Compose → K8s planning)**
  - Context: overview deployment sections.
  - Prompts: 3.2, 21, Documentation Update, Release Readiness.

- **Security (Vault, audit log, WAF)**
  - Context: 2.6 Security Audit.
  - Prompts: 3.2, 21, 4.1 Backend Implementation, 4.2 DB Implementation, 22, 23.

---

## 3. P2 – 6-Month Scale and Product Moat

High-level items, to be broken into tickets later.[file:24]

- **Search & RAG**
  - Elasticsearch indexing.
  - Vector embeddings and RAG pipeline.
  - Prompts: 2.4 Integration Audit, 2.5 Agent Audit, 3.2, 21, 4.4 Integration Implementation, 22, 23.

- **Model Lifecycle**
  - Model registry, A/B testing, feature store.
  - Prompts: 2.5 Agent Audit, 3.2, 21, Implementation, Testing, Release Readiness.

- **Billing & Usage**
  - Stripe integration, subscription, usage metering.
  - Prompts: 2.4 Integration Audit, 3.2, 21, 4.4 Integration Implementation, 22, 23.

- **Enterprise Portal**
  - Org admin dashboard, user management, API keys.
  - Prompts: 2.8 Frontend Audit, 3.2, 21, 4.5 Frontend & API Implementation, 22, 23.

- **Crawl Pipeline & Performance**
  - Distributed crawling, retry, status dashboards, CDN, caching.
  - Prompts: 2.4 Integration Audit, 2.7 Performance Audit, 3.2, 21, 4.4 Implementation, 22, 23.

---

## 4. Status Tracking

For each P0/P1/P2 item above, track:

- Status: TODO / IN PROGRESS / DONE
- Last updated: YYYY-MM-DD
- Related tickets: IDs in your issue tracker.
- Related prompts used: e.g., “Used 2.3, 3.2, 21, 4.2 Plan+Code, 22, 23”.

Update `fixes-log.md` after each completed item and ensure Documentation Update + Release Readiness prompts are run before production deployment.
