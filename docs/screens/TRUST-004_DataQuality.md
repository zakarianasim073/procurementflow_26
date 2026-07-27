# TRUST-004: Data Quality Screen Specification

**Module:** `features/data-quality/DataQualityPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Data quality monitoring, validation rules, error tracking, and data integrity management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Data Quality                  │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DataQualityHeader (score, last check)            │
│          ├──────────────────────────────────────────────────┤
│          │ DataQualityMonitor (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ QualityScore (overall gauge)                │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Rules] [Errors] [Trends] [Fixes]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ValidationRules (rule cards)                │   │
│          │ │ ErrorLog (data errors)                      │   │
│          │ │ QualityTrends (charts)                      │   │
│          │ │ AutoFixes (suggested fixes)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (quality insights, fix suggestions)                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DataQualityPage
├── ExecutiveHeader
├── Breadcrumb
├── DataQualityHeader
│   ├── Gauge (quality_score)
│   ├── KpiStrip (total_rules, errors, warnings)
│   └── Button (Run Validation)
├── DataQualityMonitor
│   ├── QualityScore
│   │   └── Gauge (overall_score)
│   ├── Tabs
│   │   ├── RulesTab
│   │   │   └── ValidationRules
│   │   │       └── RuleCard × N
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── status (pass/fail)
│   │   │           └── error_count
│   │   ├── ErrorsTab
│   │   │   └── ErrorLog
│   │   │       └── Table<DataError>
│   │   │           ├── timestamp
│   │   │           ├── source
│   │   │           ├── message
│   │   │           └── severity
│   │   ├── TrendsTab
│   │   │   └── QualityTrends
│   │   │       ├── Chart (score over time)
│   │   │       └── Chart (errors over time)
│   │   └── FixesTab
│   │       └── AutoFixes
│   │           └── FixCard × N
│   │               ├── description
│   │               ├── impact
│   │               └── Button (Apply Fix)
│   └── ValidationRunner
│       ├── Progress (validation progress)
│       └── Results (validation results)
└── AiDock
    ├── AgentCard (Data Agent)
    └── EvidencePanel (quality insights)
```

## Data Sources

### Quality Score
```typescript
// API: GET /api/v1/admin/data-quality/score
interface QualityScore {
  overall_score: number;
  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  error_count: number;
  warning_count: number;
  last_check: string;
}
```

### Validation Rules
```typescript
// API: GET /api/v1/admin/data-quality/rules
interface ValidationRuleList {
  rules: ValidationRule[];
}

interface ValidationRule {
  rule_id: string;
  name: string;
  description: string;
  category: string;
  status: 'pass' | 'fail' | 'warning';
  error_count: number;
  last_checked: string;
}
```

### Data Errors
```typescript
// API: GET /api/v1/admin/data-quality/errors
interface DataErrorList {
  errors: DataError[];
  total_count: number;
}

interface DataError {
  error_id: string;
  timestamp: string;
  source: string;
  record_id: string;
  field: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
  auto_fixable: boolean;
}
```

### React Query
```typescript
const { data: score } = useQuery({
  queryKey: ['admin', 'data-quality', 'score'],
  queryFn: () => api.get('/api/v1/admin/data-quality/score'),
  refetchInterval: 60_000, // 1 minute
});

const { data: rules } = useQuery({
  queryKey: ['admin', 'data-quality', 'rules'],
  queryFn: () => api.get('/api/v1/admin/data-quality/rules'),
});

const { data: errors } = useQuery({
  queryKey: ['admin', 'data-quality', 'errors', filters],
  queryFn: () => api.get('/api/v1/admin/data-quality/errors', { params: filters }),
});

const runValidation = useMutation({
  mutationFn: () => api.post('/api/v1/admin/data-quality/validate'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'data-quality'] });
    toast.success('Validation completed');
  },
});

const applyFix = useMutation({
  mutationFn: (errorId: string) => api.post(`/api/v1/admin/data-quality/errors/${errorId}/fix`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'data-quality'] });
    toast.success('Fix applied');
  },
});
```

## Zustand Store
```typescript
// stores/dataQualityStore.ts
interface DataQualityState {
  activeTab: string;
  autoRefresh: boolean;
  setTab: (tab: string) => void;
  setAutoRefresh: (enabled: boolean) => void;
}
```

## Interactions

### Run Validation
1. Click "Run Validation"
2. Show progress
3. Update score
4. Show results

### View Errors
1. Click Errors tab
2. Filter by severity/source
3. Click error for details
4. Apply fix if available

### Apply Fix
1. Click "Apply Fix" button
2. Confirm fix
3. Apply to data
4. Refresh quality score

### View Trends
1. Click Trends tab
2. View score over time
3. Analyze error patterns
4. Export report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Score: Skeleton gauge
- Rules: Skeleton cards
- Errors: Skeleton table
- Trends: Skeleton charts

## Error States
- Validation failure: Error details
- Fix failure: Retry button
- Network error: Toast notification

## Accessibility
- Score announced via `aria-live`
- Errors are focusable
- Screen reader: "Quality score: 85%"
- Keyboard: Enter to apply fix

## Telemetry
- `data_quality.view` — Screen loaded
- `data_quality.validate` — Validation run
- `data_quality.fix` — Fix applied
- `data_quality.export` — Report exported

## Implementation Notes
- QualityScore gauge for overview
- ValidationRules for rule management
- ErrorLog for error tracking
- QualityTrends for historical view
- AutoFixes for suggested fixes
