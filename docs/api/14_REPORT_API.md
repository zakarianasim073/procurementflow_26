# Report API Contract

**Router**: `/api/v1/reports`  
**Tags**: `reports`  
**Auth**: JWT (tenant-scoped)

---

## Overview

Report API for **executive reporting**, **analysis summaries**, and **compliance documentation** across the ProcureFlow platform. Core to **executive decision support**, **regulatory compliance**, and **stakeholder communication**. Provides standardized report generation in multiple formats (Excel, PDF, JSON) with customizable templates and scheduling.

**Primary Use Cases**:
- Executive dashboard reports (weekly/monthly/quarterly)
- Compliance and audit reports
- Market analysis reports
- Contractor performance reports
- Bid analysis reports
- Regulatory compliance reports (PPR2025)

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/reports` | List available report templates | JWT |
| POST | `/reports/generate` | Generate new report | JWT |
| GET | `/reports/{report_id}` | Get report metadata and status | JWT |
| GET | `/reports/{report_id}/download` | Download generated report file | JWT |
| GET | `/reports/{report_id}/preview` | Preview report content | JWT |
| POST | `/reports/schedule` | Schedule recurring report generation | JWT |
| GET | `/reports/schedule/{schedule_id}` | Get schedule details | JWT |
| DELETE | `/reports/schedule/{schedule_id}`
| GET | `/reports/templates/{template_id}` | Get report template details | JWT |
| POST | `/reports/templates` | Create new report template | JWT |

---

## Request/Response Schemas

### `GET /reports`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | `""` | Filter by report type (`executive`, `compliance`, `analysis`, `audit`) |
| `template` | string | `""` | Filter by template name |
| `format` | string | `""` | Filter by format (`excel`, `pdf`, `json`) |
| `created_after` | string | `""` | Filter by creation date (ISO format) |
| `created_before` | string | `""` | Filter by creation date (ISO format) |
| `limit` | int | 50 | Results per page (1-200) |
| `offset` | int | 0 | Pagination offset |

**Response (200)**
```json
{
  "success": true,
  "reports": [
    {
      "id": "uuid",
      "template_id": "executive_dashboard_v2",
      "template_name": "Executive Dashboard",
      "description": "Monthly executive performance dashboard",
      "type": "executive",
      "format": "excel",
      "parameters": {
        "periods": ["2026-01", "2026-02", "2026-03"],
        "agencies": ["BWDB", "PWD"],
        "include_charts": true,
        "include_benchmarks": true
      },
      "status": "draft|generating|completed|failed",
      "generated_at": "2026-07-21T10:30:00Z",
      "size_bytes": 1048576,
      "download_url": "/api/v1/reports/uuid/download",
      "preview_url": "/api/v1/reports/uuid/preview",
      "created_by": "user-uuid",
      "created_at": "2026-07-21T10:30:00Z",
      "updated_at": "2026-07-21T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 247,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### `POST /reports/generate`

**Request**
```json
{
  "template_id": "executive_dashboard_v2",
  "parameters": {
    "periods": ["2026-01", "2026-02", "2026-03"],
    "agencies": ["BWDB", "PWD"],
    "include_charts": true,
    "include_benchmarks": true,
    "output_format": "excel"
  },
  "tender_filter": {
    "agency": "BWDB",
    "zone": "A",
    "status": ["active", "pending"],
    "date_range": {
      "from": "2026-01-01",
      "to": "2026-03-31"
    }
  },
  "competitor_filter": {
    "agencies": ["BWDB"],
    "districts": ["Dhaka"],
    "minimum_awards": 5
  },
  "scheduling": {
    "schedule_type": "once",
    "send_to_recipients": [
      {"user_id": "user-uuid-1", "role": "owner"},
      {"user_id": "user-uuid-2", "role": "admin"}
    ],
    "delivery_channels": ["email", "in_app"],
    "priority": "normal"
  }
}
```

**Response (202)
```json
{
  "success": true,
  "report_id": "uuid",
  "status": "pending",
  "status_url": "/api/v1/reports/uuid",
  "estimated_completion": "2026-07-21T10:35:00Z",
  "parameters": { ... },
  "tender_filter": { ... },
  "competitor_filter": { ... },
  "scheduling": { ... }
}
```

### `GET /reports/{report_id}`

**Response (200)
```json
{
  "success": true,
  "report": {
    "id": "uuid",
    "template_id": "executive_dashboard_v2",
    "template_name": "Executive Dashboard",
    "description": "Monthly executive performance dashboard",
    "type": "executive",
    "format": "excel",
    "parameters": { ... },
    "tender_filter": { ... },
    "competitor_filter": { ... },
    "scheduling": { ... },
    "status": "completed",
    "generated_at": "2026-07-21T10:35:12Z",
    "completed_at": "2026-07-21T10:35:12Z",
    "size_bytes": 1048576,
    "file_path": "/runtime/reports/EXECUTIVE_DASHBOARD_v2020260731_103512.xlsx",
    "download_url": "/api/v1/reports/uuid/download",
    "preview_url": "/api/v1/reports/uuid/preview",
    "created_by": "user-uuid",
    "created_at": "2026-07-21T10:30:00Z",
    "updated_at": "2026-07-21T10:35:12Z",
    "metadata": {
      "rows_generated": 15,
      "columns": 42,
      "charts_included": 8,
      "data_sources": ["procurement_lifecycle", "contractors", "tenders"],
      "validation_status": "passed",
      "compliance_check": "PPR2025"
    },
    "errors": [],
    "warnings": ["Page 3: Chart data missing for PWD agency"]
  }
}
```

### `GET /reports/{report_id}/download`

**Response**: File download (Excel file)

### `GET /reports/{report_id}/preview`

**Response**: HTML preview for web viewing

### `POST /reports/schedule`

**Request**
```json
{
  "template_id": "executive_dashboard_v2",
  "parameters": { ... },
  "schedule": {
    "cron_expression": "0 9 * * 1-5", // Every weekday at 9 AM
    "timezone": "Asia/Dhaka",
    "start_date": "2026-08-01",
    "end_date": "2026-12-31",
    "max_executions": 12
  },
  "recipients": [
    {"user_id": "user-uuid-1", "role": "owner"},
    {"user_id": "user-uuid-2", "role": "admin"}
  ],
  "delivery": {
    "channels": ["email", "in_app"],
    "format": "excel"
  }
}
```

**Response (200)
```json
{
  "success": true,
  "schedule_id": "uuid",
  "schedule": {
    "id": "uuid",
    "cron_expression": "0 9 * * 1-5",
    "timezone": "Asia/Dhaka",
    "start_date": "2026-08-01",
    "end_date": "2026-12-31",
    "max_executions": 12,
    "next_run": "2026-08-01T09:00:00+06:00",
    "last_executed": null,
    "status": "active"
  }
}
```

### `GET /reports/schedule/{schedule_id}`

**Response (200)
```json
{
  "success": true,
  "schedule": {
    "id": "uuid",
    "cron_expression": "0 9 * * 1-5",
    "timezone": "Asia/Dhaka",
    "start_date": "2026-08-01",
    "end_date": "2026-12-31",
    "max_executions": 12,
    "next_run": "2026-08-01T09:00:00+06:00",
    "last_executed": "2026-07-21T09:00:00+06:00",
    "last_execution_result": {
      "status": "completed",
      "report_id": "uuid",
      "executed_at": "2026-07-21T09:00:00+06:00"
    },
    "status": "active",
    "created_at": "2026-07-21T10:30:00Z",
    "updated_at": "2026-07-21T10:30:00Z"
  }
}
```

### `DELETE /reports/schedule/{schedule_id}`

**Response (200)
```json
{
  "success": true,
  "message": "Schedule deleted successfully"
}
```

### `GET /reports/templates/{template_id}`

**Response (200)
```json
{
  "success": true,
  "template": {
    "id": "executive_dashboard_v2",
    "name": "Executive Dashboard",
    "description": "Monthly executive performance dashboard with KPIs, charts, and benchmarks",
    "type": "executive",
    "category": "executive",
    "formats": ["excel", "pdf", "json"],
    "parameters": {
      "periods": {
        "type": "array",
        "description": "List of time periods (YYYY-MM)",
        "default": ["2026-01", "2026-02", "2026-03"],
        "validation": {
          "max_items": 12,
          "date_format": "YYYY-MM"
        }
      },
      "agencies": {
        "type": "array",
        "description": "Agencies to include",
        "default": ["BWDB", "PWD", "LGED"],
        "validation": {
          "allowed_values": ["BWDB", "PWD", "LGED", "BPDB"]
        }
      },
      "include_charts": {
        "type": "boolean",
        "description": "Include charts in report",
        "default": true
      },
      "include_benchmarks": {
        "type": "boolean",
        "description": "Include market benchmarks",
        "default": true
      }
    },
    "metadata": {
      "version": "2.0",
      "created_by": "admin",
      "created_at": "2026-01-15T10:00:00Z",
      "last_modified": "2026-07-20T14:30:00Z",
      "tags": ["executive", "dashboard", "performance"],
      "access_level": "public"
    },
    "content_template": {
      "title": "Executive Dashboard - {{period}}",
      "sections": [
        "overview",
        "key_metrics",
        "agency_breakdown",
        "market_analysis",
        "competitive_landscape",
        "trends"
      ],
      "styles": {
        "primary_font": "Arial",
        "header_color": "#2E7D32",
        "chart_theme": "light"
      }
    }
  }
}
```

### `POST /reports/templates`

**Request**
```json
{
  "name": "Q4 Executive Report",
  "description": "Fourth quarter executive performance report",
  "type": "executive",
  "category": "quarterly",
  "formats": ["excel", "pdf"],
  "parameters": { ... },
  "content_template": { ... },
  "access_level": "public",
  "tags": ["executive", "quarterly", "summary"],
  "version": "1.0"
}
```

**Response (201)
```json
{
  "success": true,
  "template": {
    "id": "q4_executive_report_v1",
    "name": "Q4 Executive Report",
    "description": "Fourth quarter executive performance report",
    "type": "executive",
    "category": "quarterly",
    "formats": ["excel", "pdf"],
    "parameters": { ... },
    "content_template": { ... },
    "access_level": "public",
    "tags": ["executive", "quarterly", "summary"],
    "version": "1.0",
    "created_by": "user-uuid",
    "created_at": "2026-07-21T10:30:00Z"
  }
}
```

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `REPORT_NOT_FOUND` | 404 | Report ID not found |
| `REPORT_GENERATION_FAILED` | 500 | Report generation error |
| `TEMPLATE_NOT_FOUND` | 404 | Template ID not found |
| `SCHEDULE_NOT_FOUND` | 404 | Schedule ID not found |

---

## Permission Requirements

| Endpoint | Required Role | Notes |
|----------|---------------|-------|
| `/reports` | `viewer` or higher | List available reports |
| `/reports/generate` | `estimator` or `admin` | Generate new reports |
| `/reports/{id}` | `viewer` | Access specific report |
| `/reports/{id}/download` | `viewer` | Download report files |
| `/reports/{id}/preview` | `viewer` | Preview report |
| `/reports/schedule` | `admin` | Schedule report generation |
| `/reports/schedule/{id}` | `admin` | Manage schedules |
| `/reports/templates` | `admin` | Create report templates |
| `/reports/templates/{id}` | `viewer` | Get template details |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/reports` | 30 | 60 |
| `/reports/generate` | 5 | 60 |
| `/reports/schedule` | 10 | 60 |
| `/reports/templates` | 20 | 60 |

---

## Caching

- `GET /reports/{id}`: `private, max-age=300` (report metadata)
- `GET /reports/{id}/download`: `private, max-age=0` (streaming)
- `GET /reports/templates/{id}`: `public, max-age=3600` (templates)
- `GET /reports/schedule/{id}`: `private, max-age=60` (schedule configs)

---

## React Query Mapping

```typescript
export const reportKeys = {
  all: () => ['reports'] as const,
  list: (params: ReportListParams) => [...reportKeys.all, 'list', params] as const,
  generate: () => [...reportKeys.all, 'generate'] as const,
  detail: (id: string) => [...reportKeys.all, 'detail', id] as const,
  download: (id: string) => [...reportKeys.all, 'download', id] as const,
  preview: (id: string) => [...reportKeys.all, 'preview', id] as const,
  schedule: (id: string) => [...reportKeys.all, 'schedule', id] as const,
  templates: (id?: string) => [...reportKeys.all, 'templates', { id }] as const,
};

export function useReports(params: ReportListParams) {
  return useQuery({
    queryKey: reportKeys.list(params),
    queryFn: () => apiFetch<ReportListResponse>('/reports', { params }),
    staleTime: 60_000,
  });
}

export function useGenerateReport() {
  return useMutation({
    mutationFn: (data: GenerateReportRequest) => apiFetch<ReportResponse>('/reports/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
    onSuccess: () => {
      // Invalidate reports list after generation
      queryClient.invalidateQueries({ queryKey: reportKeys.all });
    },
  });
}
```

---

## Integration Points

### Executive Dashboard
```
GET /executive/overview → Executive KPIs
  ↓
POST /reports/generate (template: executive_dashboard)
  ↓
Generate comprehensive executive report
  └─ Include live data from: dashboard, intelligence, competitors
```

### Compliance Reporting
```
GET /procurement/lifecycle/stats → Compliance data
  ↓
POST /reports/generate (template: compliance_report)
  └─ Generate PPR2025 compliance report
```

### Scheduled Reporting
```
POST /reports/schedule → Quarterly reports
  ↓
System scheduler executes
  └─ POST /reports/generate → Generate and deliver
```

---

## Versioning

- `v1`: Current (report generation, templates, scheduling)
- `v2` (planned): Real-time report updates, WebSocket streaming

---

## Configuration Options

Environment variables:
- `REPORT_MAX_FILE_SIZE=50MB` (default: 50MB)
- `REPORT_MAX_GENERATION_TIME=3600` (seconds, default: 1 hour)
- `REPORT_CACHE_TTL=1800` (seconds)
- `REPORT_TEMPLATE_CACHE=true` (default: true)

---

## Monitoring & Telemetry

**Metrics**:
- Report generation success/failure rates
- Generation time metrics
- Download statistics
- Template usage patterns
- Scheduling success rates

**Alerts**:
- Generation time > 2 hours
- Report size > 500MB

> **Dependency**: `app/services/boq_excel_generator.py` (Excel report generation)
> **Integration**: `app/api/v1/reports.py` (Report API)
> **Queue**: Celery tasks for scheduled report generation

---

## OpenAPI Reference

See `/openapi.json#/paths/~1api~1reports~1generate~1post`