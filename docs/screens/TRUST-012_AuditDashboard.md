# TRUST-012: Audit Dashboard Screen Specification

**Module:** `features/audit-dashboard/AuditDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Audit trail overview, compliance monitoring, and activity analytics.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Audit Dashboard               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AuditDashboardHeader (stats, date range)         │
│          ├──────────────────────────────────────────────────┤
│          │ AuditDashboard (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (audit metrics)                    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Activity] [Compliance]   │   │
│          │ │ [Users]                                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ AuditOverview (summary charts)              │   │
│          │ │ ActivityTimeline (recent actions)           │   │
│          │ │ ComplianceStatus (compliance metrics)       │   │
│          │ │ UserActivity (user actions breakdown)       │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (audit insights, compliance recommendations)         │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AuditDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── AuditDashboardHeader
│   ├── KpiStrip (total_actions, unique_users, compliance_rate)
│   ├── CalendarRange (date range)
│   └── Button (Export Report)
├── AuditDashboard
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   └── AuditOverview
│   │   │       ├── Chart (actions_over_time)
│   │   │       ├── Chart (by_action_type)
│   │   │       └── KpiStrip (detailed_metrics)
│   │   ├── ActivityTab
│   │   │   └── ActivityTimeline
│   │   │       └── ActivityItem × N
│   │   │           ├── avatar
│   │   │           ├── user_name
│   │   │           ├── action
│   │   │           ├── resource
│   │   │           └── timestamp
│   │   ├── ComplianceTab
│   │   │   └── ComplianceStatus
│   │   │       ├── Gauge (compliance_score)
│   │   │       ├── Table<ComplianceMetric>
│   │   │       │   ├── metric
│   │   │       │   ├── status
│   │   │       │   └── score
│   │   │       └── AiInsight × N
│   │   └── UsersTab
│   │       └── UserActivity
│   │           ├── Chart (by_user)
│   │           ├── Table<UserMetric>
│   │           │   ├── user
│   │           │   ├── actions
│   │           │   └── last_active
│   │           └── UserCard × N
│   └── AuditSummary
│       ├── KpiCard (audit_coverage)
│       ├── KpiCard (anomalies)
│       └── KpiCard (retention_days)
└── AiDock
    ├── AgentCard (Audit Agent)
    └── EvidencePanel (audit insights)
```

## Data Sources

### Audit Dashboard
```typescript
// API: GET /api/v1/audit/dashboard
interface AuditDashboard {
  stats: AuditStats;
  trends: AuditTrend[];
  compliance: ComplianceMetrics;
  user_activity: UserActivityMetrics;
}

interface AuditStats {
  total_actions: number;
  unique_users: number;
  compliance_rate: number;
  anomalies_detected: number;
  avg_actions_per_user: number;
}

interface AuditTrend {
  date: string;
  actions: number;
  users: number;
}

interface ComplianceMetrics {
  score: number;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
}

interface UserActivityMetrics {
  top_users: UserMetric[];
  activity_by_type: Record<string, number>;
}

interface UserMetric {
  user_id: string;
  user_name: string;
  actions_count: number;
  last_active: string;
}
```

### React Query
```typescript
const { data: dashboard } = useQuery({
  queryKey: ['audit', 'dashboard', dateRange],
  queryFn: () => api.get('/api/v1/audit/dashboard', { params: dateRange }),
  refetchInterval: 60_000, // 1 minute
});
```

## Zustand Store
```typescript
// stores/auditDashboardStore.ts
interface AuditDashboardState {
  dateRange: { start: string; end: string };
  setRange: (range: { start: string; end: string }) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View summary charts
3. Analyze trends
4. Review metrics

### Monitor Activity
1. Click Activity tab
2. View recent actions
3. Analyze patterns
4. Identify anomalies

### Check Compliance
1. Click Compliance tab
2. View compliance score
3. Review metrics
4. Read AI insights

### Analyze Users
1. Click Users tab
2. View user activity
3. Identify top users
4. Review patterns

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Charts: Skeleton with shimmer
- Timeline: Skeleton items
- Compliance: Skeleton gauge

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Charts have table fallback
- Metrics announced via `aria-live`
- Screen reader: "Compliance rate: 95%"
- Keyboard: Tab through elements

## Telemetry
- `audit_dashboard.view` — Screen loaded
- `audit_dashboard.tab_switch` — Tab changed
- `audit_dashboard.export` — Report exported

## Implementation Notes
- Overview with summary charts
- Real-time activity timeline
- Compliance monitoring
- AiDock provides audit insights
- Export for reporting
