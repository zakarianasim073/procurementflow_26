# SEQ-001: BOQ Upload & SOR Comparison

```mermaid
sequenceDiagram
    autonumber
    actor User as Frontend User
    participant API as POST /api/boq/upload
    participant FS as File Storage
    participant CMP as POST /api/boq/compare
    participant PDF as PDFParser
    participant BOQ as BOQProcessor
    participant SOR as SOR Service
    participant DB as PostgreSQL
    participant XL as BOQExcelGenerator

    User->>API: Upload BOQ PDF (multipart)
    API->>FS: Save to uploads/{file_id}.pdf
    API-->>User: { job_id, status: "uploaded" }

    User->>CMP: POST /api/boq/compare { boq_file_id, sor_agency, zone }
    CMP->>DB: Create boq_jobs row (status: processing)

    CMP->>PDF: pdfplumber.extract(file_path)
    PDF-->>CMP: Raw BOQ table rows

    CMP->>BOQ: BOQProcessor.compare(items, agency, zone)
    loop For each BOQ item
        BOQ->>SOR: find_rate(code, desc, agency, zone)
        SOR-->>BOQ: { sor_rate, matched_code, confidence }
        BOQ->>BOQ: Compute diff, pct_diff, flag
    end
    BOQ-->>CMP: ComparisonResult[]

    CMP->>DB: Persist Tender + BOQItem rows
    CMP->>DB: Persist BOQComparison row
    CMP->>XL: generate_boq_excel(comparison)
    XL-->>CMP: Excel file path

    CMP-->>User: { job_id, status: "completed" }

    User->>CMP: GET /api/boq/jobs/{id}/result
    CMP->>DB: Fetch BOQComparison + BOQItems
    CMP-->>User: Full comparison data + Excel download URL
```

## Participants

| Actor/Component | Type | Description |
|----------------|------|-------------|
| Frontend User | Actor | Browser SPA initiating upload and comparison |
| POST /api/boq/upload | API | FastAPI endpoint for file upload |
| File Storage | Infra | Local filesystem `uploads/` directory |
| POST /api/boq/compare | API | FastAPI endpoint triggering comparison |
| PDFParser | Service | pdfplumber-based PDF text/table extraction |
| BOQProcessor | Service | Core matching engine against SOR databases |
| SOR Service | Service | In-memory SOR rate lookup (3 agencies) |
| PostgreSQL | DB | Persistent storage for jobs, items, comparisons |
| BOQExcelGenerator | Service | Multi-tab Excel report generation |

## Error Paths

1. **Invalid PDF** — `PDFParser` raises `ValueError` → API returns 422
2. **No BOQ table found** — `BOQProcessor` returns empty → API returns 404 with message
3. **SOR match failure** — Items without matches get `flag: "NO_SOR_MATCH"` in results
4. **Storage quota exceeded** — `FileUploadService` rejects before save → 413

## Timing

| Phase | Expected Duration |
|-------|-------------------|
| File upload + save | < 2s |
| PDF extraction | 3-15s (depends on PDF size) |
| SOR matching (per item) | < 50ms |
| Total comparison (100 items) | 5-20s |
| Excel generation | 2-5s |
