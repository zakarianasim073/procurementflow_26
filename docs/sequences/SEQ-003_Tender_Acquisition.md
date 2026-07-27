# SEQ-003: Full Tender Acquisition Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Trigger as API / Idle Cycle
    participant Agent as TenderAcquisitionAgent (agent-002)
    participant Lock as Distributed Lock (Redis)
    participant Brain as AgentBrain
    participant eGP as eGP Client
    participant Sub as _sub_dl.py (Subprocess)
    participant PDF as pdfplumber
    participant FS as File Storage (uploads/{tender_id}/)
    participant KB as Knowledge Entries (DB)

    Trigger->>Brain: execute(agent-002, { tender_id })
    Brain->>Agent: run(context)

    Agent->>Lock: Acquire lock(tender_id)
    Lock-->>Agent: OK (or FAIL if already running)

    rect rgb(240, 248, 255)
        Note over Agent,Sub: Phase 1: Download Notice PDF
        Agent->>Sub: python _sub_dl.py --tender-id {id} --mode notice
        Sub->>eGP: GET /GeneratePdf?reqURL=...ViewTender.jsp&id={id}
        eGP-->>Sub: PDF binary
        Sub->>FS: Save uploads/{id}/notice.pdf
        Sub-->>Agent: notice.pdf saved
    end

    rect rgb(240, 255, 240)
        Note over Agent,Sub: Phase 2: Download All-Documents ZIP
        Agent->>Sub: python _sub_dl.py --tender-id {id} --mode zip
        Sub->>eGP: GET /TenderSecUploadServlet?tenderId={id}&funName=zipdownload
        eGP-->>Sub: ZIP binary
        Sub->>FS: Save + extract to uploads/{id}/
        Sub-->>Agent: { section_count, files[] }
    end

    rect rgb(255, 248, 240)
        Note over Agent,Sub: Phase 3: Scrape Individual Sections
        Agent->>Sub: python _sub_dl.py --tender-id {id} --mode sections
        Sub->>eGP: GET /tenderer/TenderDocView.jsp?tenderId={id}
        eGP-->>Sub: HTML listing
        Sub->>eGP: Download individual PDFs/DOCX
        Sub->>FS: Save section files
        Sub-->>Agent: { downloaded_files[] }
    end

    rect rgb(248, 240, 255)
        Note over Agent,KB: Phase 4: Extract & Store Knowledge
        Agent->>PDF: Extract BOQ text from Section6 PDF
        PDF-->>Agent: boq_text (up to 50K chars)
        Agent->>PDF: Extract TDS text from Section2 PDF
        PDF-->>Agent: tds_text (up to 50K chars)

        Agent->>Brain: store_knowledge(agent-002, "boq_text", tender_id, boq_text)
        Brain->>KB: INSERT knowledge_entries
        Agent->>Brain: store_knowledge(agent-002, "tds_text", tender_id, tds_text)
        Brain->>KB: INSERT knowledge_entries
        Agent->>Brain: store_knowledge(agent-002, "tender_document", tender_id, metadata)
        Brain->>KB: INSERT knowledge_entries
    end

    Agent->>Lock: Release lock(tender_id)
    Agent->>Brain: broadcast("acquisition_complete", tender_id)
    Agent-->>Brain: AgentResult(status=SUCCESS)
```

## Participants

| Actor/Component | Type | Description |
|----------------|------|-------------|
| API / Idle Cycle | Trigger | Manual API call or automatic idle cycle |
| TenderAcquisitionAgent | Agent | Orchestrates full document acquisition |
| Distributed Lock | Infra | Redis-based lock preventing concurrent downloads |
| AgentBrain | Agent Core | Knowledge storage + inter-agent messaging |
| eGP Client | External | HTTP client for eprocure.gov.bd portal |
| _sub_dl.py | Subprocess | Clean Python process for download (bypasses WinError 10060) |
| pdfplumber | Lib | PDF text extraction |
| File Storage | Infra | `backend/uploads/{tender_id}/` directory |
| Knowledge Entries | DB | PostgreSQL knowledge_entries table |

## Phases

| Phase | Duration | Output |
|-------|----------|--------|
| Notice PDF | 5-15s | notice.pdf |
| ZIP Download | 15-60s | Extracted sections |
| Section Scrape | 10-30s | Individual PDFs/DOCX |
| Knowledge Extraction | 5-20s | 3 knowledge entries |
| **Total** | **35-125s** | Complete tender package |

## Error Paths

1. **Lock already held** — Another acquisition running → return cached status
2. **e-GP session expired** — eGPClient re-authenticates, retries once
3. **ZIP download fails** — Subprocess retries 2x, falls back to individual downloads
4. **PDF extraction fails** — Empty boq_text/tds_text stored with warning flags
