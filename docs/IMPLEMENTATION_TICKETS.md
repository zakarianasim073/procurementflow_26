# Phase J: Implementation Tickets

> Enterprise Architecture Pack implementation tickets. Extends IMPLEMENTATION_ROADMAP.md.

---

## Summary

| Category | Tickets | Status |
|----------|---------|--------|
| Documentation Pack | EAP-001 to EAP-010 | Partial ✅ (EAP-001, EAP-009) |
| Frontend Implementation | EAP-011 to EAP-025 | Ready |
| Backend Integration | EAP-026 to EAP-035 | Partial ✅ (EAP-026, EAP-027) |
| Testing & QA | EAP-036 to EAP-045 | Ready |
| DevOps & Deployment | EAP-046 to EAP-055 | Completed ✅ |
| Agent Enhancements | EAP-056 to EAP-065 | Ready |
| Knowledge System | EAP-066 to EAP-075 | Ready |
| Enterprise Features | EAP-076 to EAP-085 | Ready |
| Performance & Scale | EAP-086 to EAP-095 | Partial ✅ (EAP-086) |
| Security Hardening | EAP-096 to EAP-105 | Partial ✅ (EAP-096, EAP-097) |

---

## Documentation Pack (EAP-001 to EAP-010)

### EAP-001: API Contract Validation Tests
- **Priority**: P0
- **Area**: Testing
- **Problem**: 20 API contracts defined in docs/api/ but no tests validate implementation matches
- **Goal**: Write integration tests for all 20 API endpoints that validate request/response schemas match contracts
- **Affected**: `tests/test_api_contracts.py`, API routers
- **Dependencies**: none
- **Acceptance**: All 20 contract tests pass; response schemas match docs/api/*.md exactly
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 3 days

### EAP-002: Component Contract Storybook
- **Priority**: P1
- **Area**: Frontend
- **Problem**: 80 component contracts defined but no visual reference
- **Goal**: Create Storybook stories for all 80 components matching Phase B contracts
- **Affected**: `frontend_v2/src/**/*.stories.tsx`
- **Dependencies**: none
- **Acceptance**: All 80 components have Storybook stories with props matching contracts
- **Effort**: 5 days

### EAP-003: Screen Specification Playwright Tests
- **Priority**: P1
- **Area**: Testing
- **Problem**: 100 screen specs defined but no E2E tests validate implementation
- **Goal**: Write Playwright tests for critical screens (top 20 by usage)
- **Affected**: `tests/e2e/test_screens.spec.ts`
- **Dependencies**: EAP-002
- **Acceptance**: Top 20 screens have passing E2E tests
- **Effort**: 5 days

### EAP-004: Sequence Diagram Validation
- **Priority**: P2
- **Area**: Documentation
- **Problem**: 15 sequence diagrams need validation against actual implementation
- **Goal**: Review each diagram against code, update discrepancies
- **Affected**: `docs/sequences/*.md`
- **Dependencies**: none
- **Acceptance**: All diagrams match actual code flow
- **Effort**: 2 days

### EAP-005: Architecture Diagram Validation
- **Priority**: P2
- **Area**: Documentation
- **Problem**: 10 architecture diagrams need validation
- **Goal**: Review each diagram against actual system, update discrepancies
- **Affected**: `docs/architecture/*.md`
- **Dependencies**: none
- **Acceptance**: All diagrams match actual architecture
- **Effort**: 2 days

### EAP-006: Database ER Diagram Validation
- **Priority**: P2
- **Area**: Documentation
- **Problem**: 5 ER diagrams need validation against actual schema
- **Goal**: Review each diagram against actual PostgreSQL schema
- **Affected**: `docs/database/*.md`
- **Dependencies**: none
- **Acceptance**: All ER diagrams match actual schema
- **Effort**: 1 day

### EAP-007: Agent Spec Validation
- **Priority**: P2
- **Area**: Documentation
- **Problem**: 49 agent specs need validation against actual implementation
- **Goal**: Review each agent spec against actual code
- **Affected**: `docs/agents/*.md`
- **Dependencies**: none
- **Acceptance**: All agent specs match actual implementation
- **Effort**: 3 days

### EAP-008: Event Contract Tests
- **Priority**: P1
- **Area**: Backend
- **Problem**: 23 event schemas defined but no tests validate publishing
- **Goal**: Write tests that validate events are published in correct format
- **Affected**: `tests/test_events.py`
- **Dependencies**: none
- **Acceptance**: All event publishing matches docs/events/*.md schemas
- **Effort**: 2 days

### EAP-009: ADR Implementation Verification
- **Priority**: P1
- **Area**: Architecture
- **Problem**: 30 ADRs defined but compliance not verified
- **Goal**: Audit codebase against all 30 ADRs, document gaps
- **Affected**: `docs/adr_compliance_report.md`
- **Dependencies**: none
- **Acceptance**: Compliance report created with pass/fail for each ADR
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 3 days

### EAP-010: Enterprise Architecture Pack Index
- **Priority**: P0
- **Area**: Documentation
- **Problem**: Need master index linking all enterprise architecture pack documents
- **Goal**: Create comprehensive INDEX.md linking all phases (A-J)
- **Affected**: `docs/ENTERPRISE_ARCHITECTURE_PACK.md`
- **Dependencies**: All other EAP tickets
- **Acceptance**: Master index links all documents with status
- **Effort**: 1 day

---

## Frontend Implementation (EAP-011 to EAP-025)

### EAP-011: TEN Workspace Navigation Integration
- **Priority**: P0
- **Area**: Frontend
- **Problem**: New TEN pages created but not fully integrated into workspace navigation
- **Goal**: Verify all TEN routes work, navigation highlights correctly, back/forward works
- **Affected**: `App.tsx`, `workspaces.ts`, TEN pages
- **Dependencies**: none
- **Acceptance**: All 5 TEN sub-pages accessible via navigation, correct breadcrumbs
- **Effort**: 1 day

### EAP-012: KNOW Workspace Navigation Integration
- **Priority**: P0
- **Area**: Frontend
- **Problem**: New KNOW pages created but not fully integrated
- **Goal**: Verify all KNOW routes work, navigation highlights correctly
- **Affected**: `App.tsx`, `workspaces.ts`, KNOW pages
- **Dependencies**: none
- **Acceptance**: All 5 KNOW sub-pages accessible via navigation
- **Effort**: 1 day

### EAP-013: Responsive Design Audit
- **Priority**: P1
- **Area**: Frontend
- **Problem**: New pages may not be responsive
- **Goal**: Audit all new pages for mobile/tablet/desktop responsiveness
- **Affected**: All new page components
- **Dependencies**: EAP-011, EAP-012
- **Acceptance**: All pages pass responsive audit at 375px, 768px, 1024px
- **Effort**: 3 days

### EAP-014: Dark Mode Consistency
- **Priority**: P1
- **Area**: Frontend
- **Problem**: New pages may not support dark mode
- **Goal**: Verify all new pages support dark mode via Tailwind classes
- **Affected**: All new page components
- **Dependencies**: EAP-011, EAP-012
- **Acceptance**: All pages render correctly in dark mode
- **Effort**: 2 days

### EAP-015: Loading States Standardization
- **Priority**: P1
- **Area**: Frontend
- **Problem**: New pages may have inconsistent loading states
- **Goal**: Standardize all loading states using Skeleton component
- **Affected**: All new page components
- **Dependencies**: none
- **Acceptance**: All pages show Skeleton during loading
- **Effort**: 1 day

### EAP-016: Empty States Standardization
- **Priority**: P1
- **Area**: Frontend
- **Problem**: New pages may have inconsistent empty states
- **Goal**: Standardize all empty states using EmptyState component
- **Affected**: All new page components
- **Dependencies**: none
- **Acceptance**: All pages show EmptyState when no data
- **Effort**: 1 day

### EAP-017: Error Boundary Integration
- **Priority**: P1
- **Area**: Frontend
- **Problem**: New pages may not have error boundaries
- **Goal**: Wrap all new pages in error boundaries with fallback UI
- **Affected**: `App.tsx`, new page components
- **Dependencies**: none
- **Acceptance**: All pages have error boundaries, show fallback on error
- **Effort**: 1 day

### EAP-018: Keyboard Navigation
- **Priority**: P2
- **Area**: Frontend
- **Problem**: New pages may not support keyboard navigation
- **Goal**: Add keyboard shortcuts and focus management
- **Affected**: All new page components
- **Dependencies**: none
- **Acceptance**: All interactive elements keyboard accessible
- **Effort**: 2 days

### EAP-019: Screen Reader Support
- **Priority**: P2
- **Area**: Frontend
- **Problem**: New pages may not have ARIA labels
- **Goal**: Add ARIA labels to all interactive elements
- **Affected**: All new page components
- **Dependencies**: none
- **Acceptance**: All pages pass axe-core accessibility audit
- **Effort**: 2 days

### EAP-020: Performance Budget
- **Priority**: P1
- **Area**: Frontend
- **Problem**: Bundle size may exceed budget
- **Goal**: Verify all new pages meet Lighthouse performance budget
- **Affected**: Vite config, new page components
- **Dependencies**: none
- **Acceptance**: Lighthouse score > 90 for all new pages
- **Effort**: 2 days

### EAP-021: React Query DevTools Integration
- **Priority**: P2
- **Area**: Frontend
- **Problem**: No visibility into React Query cache state
- **Goal**: Add React Query DevTools in development mode
- **Affected**: `app/providers.tsx`
- **Dependencies**: none
- **Acceptance**: DevTools visible in development, hidden in production
- **Effort**: 0.5 days

### EAP-022: Zustand Store DevTools
- **Priority**: P2
- **Area**: Frontend
- **Problem**: No visibility into Zustand store state
- **Goal**: Add Zustand DevTools middleware in development
- **Affected**: Zustand stores
- **Dependencies**: none
- **Acceptance**: Store state visible in Redux DevTools
- **Effort**: 0.5 days

### EAP-023: API Error Handling Standardization
- **Priority**: P1
- **Area**: Frontend
- **Problem**: Error handling may be inconsistent across new pages
- **Goal**: Standardize error handling using shared error utilities
- **Affected**: All new page components, shared error utils
- **Dependencies**: none
- **Acceptance**: All API errors handled consistently with toast notifications
- **Effort**: 2 days

### EAP-024: Form Validation Standardization
- **Priority**: P2
- **Area**: Frontend
- **Problem**: Form validation may be inconsistent
- **Goal**: Standardize form validation using shared utilities
- **Affected**: All form components
- **Dependencies**: none
- **Acceptance**: All forms validate consistently with inline errors
- **Effort**: 2 days

### EAP-025: i18n Foundation
- **Priority**: P2
- **Area**: Frontend
- **Problem**: No internationalization support
- **Goal**: Set up i18n foundation for future localization
- **Affected**: `app/providers.tsx`, shared i18n utils
- **Dependencies**: none
- **Acceptation**: i18n setup complete, English strings extracted
- **Effort**: 3 days

---

## Backend Integration (EAP-026 to EAP-035)

### EAP-026: API Contract Compliance Audit
- **Priority**: P0
- **Area**: Backend
- **Problem**: API implementations may not match contracts
- **Goal**: Audit all API endpoints against docs/api/*.md contracts
- **Affected**: All API routers
- **Dependencies**: none
- **Acceptance**: All endpoints match contract specifications
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 3 days

### EAP-027: Missing Endpoint Implementation
- **Priority**: P0
- **Area**: Backend
- **Problem**: Some API contract endpoints may not be implemented
- **Goal**: Implement any missing endpoints from Phase A contracts
- **Affected**: API routers
- **Dependencies**: EAP-026
- **Acceptance**: All contract endpoints implemented and tested
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 5 days

### EAP-028: Response Schema Validation
- **Priority**: P1
- **Area**: Backend
- **Problem**: API responses may not match Pydantic schemas
- **Goal**: Add response validation middleware
- **Affected**: API middleware, Pydantic schemas
- **Dependencies**: none
- **Acceptance**: All API responses validated against schemas
- **Effort**: 3 days

### EAP-029: Request Validation Enhancement
- **Priority**: P1
- **Area**: Backend
- **Problem**: Request validation may be incomplete
- **Goal**: Enhance request validation for all endpoints
- **Affected**: Pydantic schemas, API routers
- **Dependencies**: none
- **Acceptance**: All endpoints validate request body, query params, path params
- **Effort**: 2 days

### EAP-030: Rate Limiter Enhancement
- **Priority**: P1
- **Area**: Backend
- **Problem**: Rate limiting may not be per-tenant
- **Goal**: Implement per-tenant rate limiting with Redis
- **Affected**: `core/rate_limiter.py`, middleware
- **Dependencies**: none
- **Acceptance**: Rate limiting works per-tenant, not globally
- **Effort**: 2 days

### EAP-031: Quota Enforcement Enhancement
- **Priority**: P1
- **Area**: Backend
- **Problem**: Quota enforcement may not be complete
- **Goal**: Add quota checks for all billable operations
- **Affected**: `services/quota_service.py`, API routers
- **Dependencies**: none
- **Acceptance**: All billable operations check quota before execution
- **Effort**: 2 days

### EAP-032: Webhook Delivery Reliability
- **Priority**: P1
- **Area**: Backend
- **Problem**: Webhook delivery may not be reliable
- **Goal**: Add retry logic, dead letter queue, and monitoring
- **Affected**: `services/webhook_service.py`
- **Dependencies**: none
- **Acceptance**: Webhooks retry 3x with exponential backoff, failures logged
- **Effort**: 2 days

### EAP-033: Audit Logging Enhancement
- **Priority**: P1
- **Area**: Backend
- **Problem**: Audit logging may not cover all operations
- **Goal**: Add audit logging to all mutating endpoints
- **Affected**: `services/audit_service.py`, API routers
- **Dependencies**: none
- **Acceptance**: All mutating operations logged to audit_events
- **Effort**: 2 days

### EAP-034: SSO Integration Testing
- **Priority**: P1
- **Area**: Backend
- **Problem**: SSO integration may not be tested
- **Goal**: Add integration tests for OIDC and SAML flows
- **Affected**: `tests/test_sso.py`, SSO routers
- **Dependencies**: none
- **Acceptance**: OIDC and SAML flows tested end-to-end
- **Effort**: 3 days

### EAP-035: RBAC Integration Testing
- **Priority**: P1
- **Area**: Backend
- **Problem**: RBAC may not be tested across all endpoints
- **Goal**: Add integration tests for all RBAC-protected endpoints
- **Affected**: `tests/test_rbac.py`, all protected routers
- **Dependencies**: none
- **Acceptance**: All protected endpoints tested with different roles
- **Effort**: 3 days

---

## Testing & QA (EAP-036 to EAP-045)

### EAP-036: SOR Golden Test Suite
- **Priority**: P0
- **Area**: Testing
- **Problem**: SOR matching accuracy needs verification
- **Goal**: Create 100+ golden tests for SOR matching
- **Affected**: `tests/test_sor_golden.py`
- **Dependencies**: none
- **Acceptance**: 100+ tests pass with known inputs/outputs
- **Effort**: 2 days

### EAP-037: BOQ Golden Test Suite
- **Priority**: P0
- **Area**: Testing
- **Problem**: BOQ comparison accuracy needs verification
- **Goal**: Create 10+ golden tests for BOQ comparison
- **Affected**: `tests/test_boq_golden.py`
- **Dependencies**: none
- **Acceptance**: 10+ tests pass with known BOQ inputs/outputs
- **Effort**: 2 days

### EAP-038: Agent Unit Test Suite
- **Priority**: P1
- **Area**: Testing
- **Problem**: 49 agents have minimal test coverage
- **Goal**: Write unit tests for all agents
- **Affected**: `tests/test_agents/`
- **Dependencies**: none
- **Acceptance**: All agents have unit tests covering main logic
- **Effort**: 10 days

### EAP-039: Service Unit Test Suite
- **Priority**: P1
- **Area**: Testing
- **Problem**: 78 services have minimal test coverage
- **Goal**: Write unit tests for critical services
- **Affected**: `tests/test_services/`
- **Dependencies**: none
- **Acceptance**: Critical services have 80%+ coverage
- **Effort**: 10 days

### EAP-040: Integration Test Suite
- **Priority**: P1
- **Area**: Testing
- **Problem**: Integration tests are sparse
- **Goal**: Write integration tests for critical workflows
- **Affected**: `tests/integration/`
- **Dependencies**: none
- **Acceptance**: All critical workflows have integration tests
- **Effort**: 5 days

### EAP-041: E2E Test Suite
- **Priority**: P1
- **Area**: Testing
- **Problem**: E2E tests are minimal
- **Goal**: Write Playwright E2E tests for critical user flows
- **Affected**: `tests/e2e/`
- **Dependencies**: EAP-003
- **Acceptance**: Critical user flows tested end-to-end
- **Effort**: 5 days

### EAP-042: Performance Test Suite
- **Priority**: P2
- **Area**: Testing
- **Problem**: No performance benchmarks
- **Goal**: Create k6 performance tests for critical endpoints
- **Affected**: `tests/performance/`
- **Dependencies**: none
- **Acceptance**: Performance benchmarks defined and baseline measured
- **Effort**: 3 days

### EAP-043: Security Test Suite
- **Priority**: P1
- **Area**: Testing
- **Problem**: Security testing is minimal
- **Goal**: Add security tests (auth bypass, RLS bypass, injection)
- **Affected**: `tests/security/`
- **Dependencies**: none
- **Acceptance**: All security attack vectors tested
- **Effort**: 3 days

### EAP-044: Load Test Suite
- **Priority**: P2
- **Area**: Testing
- **Problem**: No load testing
- **Goal**: Create load tests for critical endpoints
- **Affected**: `tests/load/`
- **Dependencies**: EAP-042
- **Acceptance**: Load tests pass at 100 concurrent users
- **Effort**: 3 days

### EAP-045: Chaos Test Suite
- **Priority**: P2
- **Area**: Testing
- **Problem**: No chaos testing
- **Goal**: Add chaos tests (DB failure, Redis failure, agent failure)
- **Affected**: `tests/chaos/`
- **Dependencies**: none
- **Acceptance**: System degrades gracefully under failure conditions
- **Effort**: 3 days

---

## DevOps & Deployment (EAP-046 to EAP-055)

### EAP-046: Docker Compose Cleanup
- **Priority**: P0
- **Area**: DevOps
- **Problem**: Docker Compose had a documentation bug — ARCH-008 and ADR-013 incorrectly labeled the container↔host port mapping (5432→5433) as a "port mismatch bug" when it is correct behavior (container-internal 5432, host 5433).
- **Goal**: Fix port documentation, clarify container vs host port distinction, add port explainer
- **Affected**: `docs/architecture/ARCH-008_Deployment.md`, `docs/architecture/ADRs.md`, `docs/ADR_BASELINE.md`
- **Dependencies**: none
- **Acceptance**: Deployment docs clearly distinguish container port (5432) from host port (5433); ADR-013 no longer marks a false "bug"
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 1 day

### EAP-047: Multi-stage Dockerfile
- **Priority**: P1
- **Area**: DevOps
- **Problem**: No multi-stage Dockerfile
- **Goal**: Create multi-stage Dockerfile for production
- **Affected**: `Dockerfile`, `Dockerfile.dev`
- **Dependencies**: none
- **Acceptance**: Production image < 500MB, dev image has all tools
- **Effort**: 2 days

### EAP-048: CI Pipeline
- **Priority**: P1
- **Area**: DevOps
- **Problem**: No CI pipeline
- **Goal**: Create GitHub Actions CI pipeline
- **Affected**: `.github/workflows/ci.yml`
- **Dependencies**: EAP-047
- **Acceptance**: CI runs lint, typecheck, tests on every PR
- **Effort**: 3 days

### EAP-049: CD Pipeline
- **Priority**: P1
- **Area**: DevOps
- **Problem**: No CD pipeline
- **Goal**: Create deployment pipeline
- **Affected**: `.github/workflows/deploy.yml`
- **Dependencies**: EAP-048
- **Acceptance**: Auto-deploy to staging on merge, manual deploy to prod
- **Effort**: 3 days

### EAP-050: Database Migration Pipeline
- **Priority**: P1
- **Area**: DevOps
- **Problem**: No automated migration pipeline
- **Goal**: Auto-run Alembic migrations on deploy
- **Affected**: `deploy/migrate.sh`, CI/CD
- **Dependencies**: EAP-049
- **Acceptance**: Migrations run automatically on deploy
- **Effort**: 1 day

### EAP-051: Monitoring Dashboard
- **Priority**: P1
- **Area**: DevOps
- **Problem**: No monitoring dashboards
- **Goal**: Create Grafana dashboards for API, DB, agents
- **Affected**: `deploy/grafana/`
- **Dependencies**: none
- **Acceptance**: Dashboards show API latency, error rates, DB connections
- **Effort**: 3 days

### EAP-052: Alerting Rules
- **Priority**: P1
- **Area**: DevOps
- **Problem**: No alerting rules
- **Goal**: Create Prometheus alerting rules
- **Affected**: `deploy/prometheus/alerts.yml`
- **Dependencies**: EAP-051
- **Acceptance**: Alerts fire on error rate > 5%, latency > 2s, DB connections > 50
- **Effort**: 2 days

### EAP-053: Log Aggregation
- **Priority**: P2
- **Area**: DevOps
- **Problem**: No centralized logging
- **Goal**: Set up log aggregation (Loki/ELK)
- **Affected**: `deploy/loki/`
- **Dependencies**: none
- **Acceptance**: All logs queryable from central location
- **Effort**: 3 days

### EAP-054: Secrets Management
- **Priority**: P1
- **Area**: DevOps
- **Problem**: Secrets may not be managed properly
- **Goal**: Set up secrets management (Vault/env injection)
- **Affected**: `deploy/secrets/`
- **Dependencies**: none
- **Acceptance**: No secrets in code, all injected at runtime
- **Effort**: 2 days

### EAP-055: Disaster Recovery Runbook
- **Priority**: P0
- **Area**: DevOps
- **Problem**: No disaster recovery plan documented
- **Goal**: Create comprehensive DR runbook with tested procedures for DB restore, app rebuild, file recovery, and monitoring stack recovery
- **Affected**: `docs/runbooks/disaster_recovery.md`
- **Dependencies**: DB-01 (backups)
- **Acceptance**: DR procedure documented and tested; runbook covers SEV-1 through SEV-3 scenarios; post-recovery verification steps included
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 2 days

---

## Agent Enhancements (EAP-056 to EAP-065)

### EAP-056: Agent Health Monitoring
- **Priority**: P1
- **Area**: Agents
- **Problem**: No agent health monitoring
- **Goal**: Add health checks for all agents
- **Affected**: `agents/core/watchdog.py`, all agents
- **Dependencies**: none
- **Acceptance**: All agents report health status
- **Effort**: 2 days

### EAP-057: Agent Metrics Collection
- **Priority**: P1
- **Area**: Agents
- **Problem**: No agent metrics
- **Goal**: Add Prometheus metrics for agent execution
- **Affected**: `agents/core/brain.py`, all agents
- **Dependencies**: none
- **Acceptance**: Agent execution time, success rate, error rate collected
- **Effort**: 2 days

### EAP-058: Agent Timeout Handling
- **Priority**: P1
- **Area**: Agents
- **Problem**: Agents may hang indefinitely
- **Goal**: Add timeout handling for all agents
- **Affected**: `agents/core/brain.py`, all agents
- **Dependencies**: none
- **Acceptance**: Agents timeout after configurable limit, return error
- **Effort**: 2 days

### EAP-059: Agent Retry Logic
- **Priority**: P1
- **Area**: Agents
- **Problem**: Agent failures may not be retried
- **Goal**: Add configurable retry logic for agents
- **Affected**: `agents/core/brain.py`, all agents
- **Dependencies**: none
- **Acceptance**: Agents retry N times with exponential backoff
- **Effort**: 2 days

### EAP-060: Agent Circuit Breaker
- **Priority**: P2
- **Area**: Agents
- **Problem**: Repeated agent failures may cause cascading issues
- **Goal**: Add circuit breaker for agent dependencies
- **Affected**: `agents/core/brain.py`
- **Dependencies**: none
- **Acceptance**: Circuit breaker opens after 5 consecutive failures
- **Effort**: 2 days

### EAP-061: Agent Progress Reporting
- **Priority**: P1
- **Area**: Agents
- **Problem**: No visibility into agent progress
- **Goal**: Add progress reporting for long-running agents
- **Affected**: All long-running agents
- **Dependencies**: none
- **Acceptance**: Agents report progress (0-100%) during execution
- **Effort**: 3 days

### EAP-062: Agent Result Caching
- **Priority**: P2
- **Area**: Agents
- **Problem**: Agent results may be recomputed unnecessarily
- **Goal**: Add result caching for deterministic agents
- **Affected**: `agents/core/brain.py`
- **Dependencies**: none
- **Acceptance**: Deterministic agents return cached results within TTL
- **Effort**: 2 days

### EAP-063: Agent Dependency Graph
- **Priority**: P2
- **Area**: Agents
- **Problem**: Agent dependencies are not visualized
- **Goal**: Add dependency graph visualization
- **Affected**: `agents/core/registry.py`
- **Dependencies**: none
- **Acceptance**: Agent dependency graph queryable via API
- **Effort**: 2 days

### EAP-064: Agent Versioning
- **Priority**: P2
- **Area**: Agents
- **Problem**: No agent versioning
- **Goal**: Add version tracking for agents
- **Affected**: `agents/core/base.py`
- **Dependencies**: none
- **Acceptance**: Each agent has version, tracked in metadata
- **Effort**: 1 day

### EAP-065: Agent A/B Testing
- **Priority**: P2
- **Area**: Agents
- **Problem**: No A/B testing capability for agents
- **Goal**: Add A/B testing framework for agent variants
- **Affected**: `agents/core/registry.py`
- **Dependencies**: none
- **Acceptance**: Agent variants can be tested with traffic splitting
- **Effort**: 3 days

---

## Knowledge System (EAP-066 to EAP-075)

### EAP-066: Knowledge Search Enhancement
- **Priority**: P1
- **Area**: Knowledge
- **Problem**: Knowledge search may not be comprehensive
- **Goal**: Enhance search with synonyms, typos, and relevance ranking
- **Affected**: `services/project_memory.py`
- **Dependencies**: none
- **Acceptance**: Search handles typos, synonyms, and ranks by relevance
- **Effort**: 3 days

### EAP-067: Knowledge Graph Enhancement
- **Priority**: P1
- **Area**: Knowledge
- **Problem**: Knowledge graph may not be complete
- **Goal**: Add more entity types and relationships
- **Affected**: `agents/core/knowledge_graph.py`
- **Dependencies**: none
- **Acceptance**: Knowledge graph covers all entity types with rich relationships
- **Effort**: 3 days

### EAP-068: Knowledge Export
- **Priority**: P2
- **Area**: Knowledge
- **Problem**: No knowledge export capability
- **Goal**: Add export to JSON/CSV/Excel
- **Affected**: `services/knowledge_export.py`
- **Dependencies**: none
- **Acceptance**: Knowledge entries exportable in multiple formats
- **Effort**: 2 days

### EAP-069: Knowledge Import
- **Priority**: P2
- **Area**: Knowledge
- **Problem**: No knowledge import capability
- **Goal**: Add import from JSON/CSV
- **Affected**: `services/knowledge_import.py`
- **Dependencies**: none
- **Acceptance**: Knowledge entries importable from external sources
- **Effort**: 2 days

### EAP-070: Knowledge Deduplication
- **Priority**: P1
- **Area**: Knowledge
- **Problem**: Knowledge entries may be duplicated
- **Goal**: Add deduplication logic
- **Affected**: `agents/core/brain.py`
- **Dependencies**: none
- **Acceptance**: Duplicate knowledge entries detected and merged
- **Effort**: 2 days

### EAP-071: Knowledge Quality Scoring
- **Priority**: P2
- **Area**: Knowledge
- **Problem**: No quality scoring for knowledge
- **Goal**: Add quality scoring based on source, recency, usage
- **Affected**: `services/knowledge_quality.py`
- **Dependencies**: none
- **Acceptance**: Each knowledge entry has quality score
- **Effort**: 2 days

### EAP-072: Knowledge Analytics
- **Priority**: P2
- **Area**: Knowledge
- **Problem**: No knowledge usage analytics
- **Goal**: Add analytics for knowledge access patterns
- **Affected**: `services/knowledge_analytics.py`
- **Dependencies**: none
- **Acceptance**: Knowledge usage patterns tracked and queryable
- **Effort**: 2 days

### EAP-073: Knowledge Backup
- **Priority**: P1
- **Area**: Knowledge
- **Problem**: Knowledge entries may be lost
- **Goal**: Add backup and restore capability
- **Affected**: `scripts/knowledge_backup.py`
- **Dependencies**: none
- **Acceptance**: Knowledge entries backupable and restorable
- **Effort**: 2 days

### EAP-074: Knowledge Retention
- **Priority**: P2
- **Area**: Knowledge
- **Problem**: No retention policy for knowledge
- **Goal**: Add configurable retention policies
- **Affected**: `services/retention_service.py`
- **Dependencies**: none
- **Acceptance**: Old knowledge entries archived/deleted per policy
- **Effort**: 2 days

### EAP-075: Knowledge Sharing
- **Priority**: P2
- **Area**: Knowledge
- **Problem**: No multi-tenant knowledge sharing
- **Goal**: Add selective knowledge sharing between tenants
- **Affected**: `services/knowledge_sharing.py`
- **Dependencies**: none
- **Acceptance**: Tenants can share specific knowledge entries
- **Effort**: 3 days

---

## Enterprise Features (EAP-076 to EAP-085)

### EAP-076: SSO Login Flow Testing
- **Priority**: P1
- **Area**: Enterprise
- **Problem**: SSO login flows untested
- **Goal**: Test OIDC and SAML login flows end-to-end
- **Affected**: `tests/test_sso.py`
- **Dependencies**: none
- **Acceptance**: OIDC and SAML login flows working
- **Effort**: 3 days

### EAP-077: RBAC Permission Matrix Testing
- **Priority**: P1
- **Area**: Enterprise
- **Problem**: RBAC permissions untested
- **Goal**: Test all permission combinations
- **Affected**: `tests/test_rbac.py`
- **Dependencies**: none
- **Acceptance**: All permission combinations tested
- **Effort**: 3 days

### EAP-078: Audit Log Query API
- **Priority**: P1
- **Area**: Enterprise
- **Problem**: No audit log query API
- **Goal**: Create API for querying audit logs
- **Affected**: `api/v2/enterprise.py`
- **Dependencies**: none
- **Acceptance**: Audit logs queryable via API with filters
- **Effort**: 2 days

### EAP-079: Webhook Management API
- **Priority**: P1
- **Area**: Enterprise
- **Problem**: No webhook management API
- **Goal**: Create API for managing webhooks
- **Affected**: `api/v2/enterprise.py`
- **Dependencies**: none
- **Acceptance**: Webhooks CRUD via API
- **Effort**: 2 days

### EAP-080: Quota Management API
- **Priority**: P1
- **Area**: Enterprise
- **Problem**: No quota management API
- **Goal**: Create API for managing quotas
- **Affected**: `api/v2/enterprise.py`
- **Dependencies**: none
- **Acceptance**: Quotas configurable via API
- **Effort**: 2 days

### EAP-081: User Management API
- **Priority**: P1
- **Area**: Enterprise
- **Problem**: No user management API
- **Goal**: Create API for managing users
- **Affected**: `api/v2/enterprise.py`
- **Dependencies**: none
- **Acceptance**: Users CRUD via API
- **Effort**: 2 days

### EAP-082: Tenant Onboarding Flow
- **Priority**: P1
- **Area**: Enterprise
- **Problem**: No tenant onboarding flow
- **Goal**: Create tenant onboarding wizard
- **Affected**: `frontend_v2/src/features/enterprise/`
- **Dependencies**: none
- **Acceptance**: New tenants onboarded via wizard
- **Effort**: 5 days

### EAP-083: Usage Metering
- **Priority**: P1
- **Area**: Enterprise
- **Problem**: No usage metering
- **Goal**: Add metering for API calls, BOQ comparisons, agent runs
- **Affected**: `services/metering_service.py`
- **Dependencies**: none
- **Acceptance**: Usage tracked per tenant per resource
- **Effort**: 3 days

### EAP-084: Billing Integration
- **Priority**: P2
- **Area**: Enterprise
- **Problem**: No billing integration
- **Goal**: Add Stripe/billing integration
- **Affected**: `services/billing_service.py`
- **Dependencies**: EAP-083
- **Acceptance**: Invoices generated from usage
- **Effort**: 5 days

### EAP-085: SLA Monitoring
- **Priority**: P2
- **Area**: Enterprise
- **Problem**: No SLA monitoring
- **Goal**: Add SLA tracking and reporting
- **Affected**: `services/sla_service.py`
- **Dependencies**: none
- **Acceptance**: SLA compliance tracked and reported
- **Effort**: 3 days

---

## Performance & Scale (EAP-086 to EAP-095)

### EAP-086: SOR Batch Lookup
- **Priority**: P0
- **Area**: Performance
- **Problem**: SOR matching does N×3 queries per BOQ item
- **Goal**: Batch SOR lookup with single query
- **Affected**: `sor/sor_service.py`, `services/boq_processor.py`
- **Dependencies**: none
- **Acceptance**: SOR lookup for 100 items in < 100ms
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 3 days

### EAP-087: Database Query Optimization
- **Priority**: P1
- **Area**: Performance
- **Problem**: Some queries may be slow
- **Goal**: Identify and optimize slow queries
- **Affected**: All service files
- **Dependencies**: none
- **Acceptance**: All queries < 100ms
- **Effort**: 5 days

### EAP-088: Connection Pool Optimization
- **Priority**: P1
- **Area**: Performance
- **Problem**: Connection pool may not be optimal
- **Goal**: Optimize pool size and timeout settings
- **Affected**: `core/config.py`, `core/database.py`
- **Dependencies**: none
- **Acceptation**: Pool handles 100 concurrent requests
- **Effort**: 2 days

### EAP-089: Caching Layer Enhancement
- **Priority**: P1
- **Area**: Performance
- **Problem**: Caching may not be optimal
- **Goal**: Add caching for hot paths
- **Affected**: `services/cache_service.py`
- **Dependencies**: none
- **Acceptance**: Hot paths served from cache < 1ms
- **Effort**: 3 days

### EAP-090: Async Optimization
- **Priority**: P1
- **Area**: Performance
- **Problem**: Some operations may be sync in async paths
- **Goal**: Identify and fix sync operations in async paths
- **Affected**: All service files
- **Dependencies**: none
- **Acceptance**: No sync operations in async paths
- **Effort**: 3 days

### EAP-091: Database Index Optimization
- **Priority**: P1
- **Area**: Performance
- **Problem**: Missing indexes on large tables
- **Goal**: Add indexes for common query patterns
- **Affected**: `alembic/versions/`
- **Dependencies**: none
- **Acceptance**: All common queries use indexes
- **Effort**: 2 days

### EAP-092: API Response Compression
- **Priority**: P2
- **Area**: Performance
- **Problem**: Large API responses not compressed
- **Goal**: Add gzip compression
- **Affected**: `main.py`
- **Dependencies**: none
- **Acceptance**: API responses compressed > 1KB
- **Effort**: 1 day

### EAP-093: Static Asset Optimization
- **Priority**: P2
- **Area**: Performance
- **Problem**: Frontend assets may not be optimized
- **Goal**: Optimize bundle size, add lazy loading
- **Affected**: `frontend_v2/vite.config.ts`
- **Dependencies**: none
- **Acceptance**: Initial bundle < 500KB
- **Effort**: 3 days

### EAP-094: Database Read Replicas
- **Priority**: P2
- **Area**: Performance
- **Problem**: No read replica support
- **Goal**: Add read replica routing for read-heavy queries
- **Affected**: `core/database.py`
- **Dependencies**: none
- **Acceptance**: Read queries routed to replicas
- **Effort**: 3 days

### EAP-095: Horizontal Scaling
- **Priority**: P2
- **Area**: Performance
- **Problem**: No horizontal scaling support
- **Goal**: Enable multiple API workers
- **Affected**: `docker-compose.yml`, `main.py`
- **Dependencies**: none
- **Acceptance**: System works with 4 API workers
- **Effort**: 3 days

---

## Security Hardening (EAP-096 to EAP-105)

### EAP-096: SQL Injection Prevention
- **Priority**: P0
- **Area**: Security
- **Problem**: SQL injection may be possible
- **Goal**: Audit all SQL queries for injection vulnerabilities
- **Affected**: All service files
- **Dependencies**: none
- **Acceptance**: No SQL injection vulnerabilities found
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 3 days

### EAP-097: XSS Prevention
- **Priority**: P0
- **Area**: Security
- **Problem**: XSS may be possible in frontend
- **Goal**: Audit all frontend rendering for XSS
- **Affected**: All frontend components
- **Dependencies**: none
- **Acceptance**: No XSS vulnerabilities found
- **Status**: ✅ Completed (2026-07-27)
- **Effort**: 2 days

### EAP-098: CSRF Protection
- **Priority**: P1
- **Area**: Security
- **Problem**: CSRF may be possible
- **Goal**: Add CSRF protection
- **Affected**: `core/security.py`
- **Dependencies**: none
- **Acceptance**: CSRF tokens required for mutating operations
- **Effort**: 2 days

### EAP-099: Input Sanitization
- **Priority**: P1
- **Area**: Security
- **Problem**: User input may not be sanitized
- **Goal**: Add input sanitization for all user inputs
- **Affected**: All Pydantic schemas
- **Dependencies**: none
- **Acceptance**: All user inputs sanitized
- **Effort**: 2 days

### EAP-100: Rate Limiting Enhancement
- **Priority**: P1
- **Area**: Security
- **Problem**: Rate limiting may not be sufficient
- **Goal**: Add per-endpoint rate limiting
- **Affected**: `core/rate_limiter.py`
- **Dependencies**: none
- **Acceptance**: All endpoints rate limited
- **Effort**: 2 days

### EAP-101: CORS Hardening
- **Priority**: P1
- **Area**: Security
- **Problem**: CORS may be too permissive
- **Goal**: Tighten CORS to specific origins
- **Affected**: `main.py`
- **Dependencies**: none
- **Acceptance**: CORS only allows specific origins
- **Effort**: 1 day

### EAP-102: Security Headers
- **Priority**: P1
- **Area**: Security
- **Problem**: No security headers
- **Goal**: Add security headers (HSTS, CSP, X-Frame-Options)
- **Affected**: `main.py`
- **Dependencies**: none
- **Acceptance**: All security headers present
- **Effort**: 1 day

### EAP-103: Dependency Vulnerability Scanning
- **Priority**: P1
- **Area**: Security
- **Problem**: Dependencies may have vulnerabilities
- **Goal**: Add dependency vulnerability scanning
- **Affected**: `.github/workflows/security.yml`
- **Dependencies**: none
- **Acceptance**: All dependencies scanned for vulnerabilities
- **Effort**: 2 days

### EAP-104: Penetration Testing
- **Priority**: P2
- **Area**: Security
- **Problem**: No penetration testing
- **Goal**: Conduct penetration testing
- **Affected**: `docs/security/pentest_report.md`
- **Dependencies**: none
- **Acceptance**: Penetration test report created
- **Effort**: 5 days

### EAP-105: Security Documentation
- **Priority**: P1
- **Area**: Security
- **Problem**: No security documentation
- **Goal**: Create security documentation
- **Affected**: `docs/security/SECURITY.md`
- **Dependencies**: none
- **Acceptance**: Security documentation complete
- **Effort**: 2 days
