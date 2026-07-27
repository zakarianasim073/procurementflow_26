# SEQ-004: Tender Radar Scanning (e-GP Discovery)

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Idle Cycle / API
    participant Agent as TenderRadarAgent (agent-001)
    participant Brain as AgentBrain
    participant eGP as eGP Client
    participant DB as PostgreSQL

    Cron->>Brain: execute(agent-001, { action: "scan_live_tenders" })
    Brain->>Agent: run(context)

    rect rgb(240, 248, 255)
        Note over Agent,eGP: Phase 1: Session Setup
        Agent->>eGP: GET https://www.eprocure.gov.bd/
        eGP-->>Agent: JSESSIONID cookie
        Agent->>eGP: POST /LoginSrBean?action=checkLogin
        eGP-->>Agent: Authenticated session
    end

    rect rgb(240, 255, 240)
        Note over Agent,DB: Phase 2: Scan Live Tenders
        loop Pages 1-5 (100 per page)
            Agent->>eGP: POST /TenderDetailsServlet { funName: "AllTenders", viewType: "Live", pageNo, size: 100 }
            eGP-->>Agent: Tender list JSON/HTML
        end
        Agent->>Agent: Filter to Works category only
        Agent->>DB: SELECT existing tender_ids FROM procurement_tenders
        Agent->>Agent: Deduplicate (skip known IDs)
    end

    rect rgb(255, 248, 240)
        Note over Agent,DB: Phase 3: Persist New Tenders
        loop For each new tender
            Agent->>DB: INSERT INTO procurement_tenders (tender_id, title, agency_code, estimated_amount, closing_date, package_no, ...)
        end
        Agent->>DB: UPDATE procurement_lifecycle (status tracking)
    end

    rect rgb(248, 240, 255)
        Note over Agent,DB: Phase 4: Optional Enrichments
        opt APP Records Scan
            Agent->>eGP: POST /TenderDetailsServlet { funName: "AllTenders", viewType: "APP" }
            Agent->>DB: INSERT INTO app_records
        end
        opt NOA Awards Scan
            Agent->>eGP: POST /SearchNoaServlet { keyword, pageNo, size }
            Agent->>DB: INSERT INTO procurement_awards
        end
    end

    Agent-->>Brain: AgentResult { live_found, new_inserted, awards_found }
```

## Participants

| Actor/Component | Type | Description |
|----------------|------|-------------|
| Idle Cycle / API | Trigger | Scheduled cron or manual trigger |
| TenderRadarAgent | Agent | e-GP discovery scanner |
| AgentBrain | Agent Core | Orchestrator + knowledge store |
| eGP Client | External | eprocure.gov.bd HTTP client |
| PostgreSQL | DB | Tender, award, and lifecycle tables |

## Data Volume

| Metric | Value |
|--------|-------|
| Pages scanned | Up to 5 (500 tenders max) |
| Filter | Works category only |
| Typical new tenders per scan | 5-20 |
| Deduplication | Tender ID against existing 395K |

## Error Paths

1. **e-GP unreachable** — Retry 3x with exponential backoff → return error status
2. **Session expired mid-scan** — Re-authenticate and resume from last page
3. **DB connection lost** — Retry with 5s delay, max 3 attempts
4. **Rate limiting** — e-GP blocks requests → back off 60s, reduce page count
