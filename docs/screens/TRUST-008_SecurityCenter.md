# TRUST-008: Security Center Screen Specification

**Module:** `features/security/SecurityCenterPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Security monitoring, access control, and threat detection dashboard.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Security Center               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SecurityCenterHeader (status, alerts)            │
│          ├──────────────────────────────────────────────────┤
│          │ SecurityCenter (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SecurityScore (overall gauge)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Access] [Logs] [Threats] │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SecurityOverview (summary charts)           │   │
│          │ │ AccessControl (permissions matrix)          │   │
│          │ │ SecurityLogs (audit trail)                  │   │
│          │ │ ThreatDetection (alerts + analysis)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (security insights, threat analysis)                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SecurityCenterPage
├── ExecutiveHeader
├── Breadcrumb
├── SecurityCenterHeader
│   ├── Gauge (security_score)
│   ├── Badge (status: secure/warning/critical)
│   └── Badge (active_alerts)
├── SecurityCenter
│   ├── SecurityScore
│   │   └── Gauge (overall_score)
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   └── SecurityOverview
│   │   │       ├── Chart (security_trend)
│   │   │       ├── Chart (incidents_by_type)
│   │   │       └── KpiStrip (metrics)
│   │   ├── AccessTab
│   │   │   └── AccessControl
│   │   │       ├── PermissionsMatrix
│   │   │       └── UserAccessList
│   │   ├── LogsTab
│   │   │   └── SecurityLogs
│   │   │       └── Table<SecurityLog>
│   │   │           ├── timestamp
│   │   │           ├── event
│   │   │           ├── user
│   │   │           └── severity
│   │   └── ThreatsTab
│   │       └── ThreatDetection
│   │           ├── ThreatAlert × N
│   │           │   ├── type
│   │           │   ├── severity
│   │           │   └── description
│   │           └── ThreatAnalysis
│   └── SecurityActions
│       ├── Button (Run Scan)
│       ├── Button (Export Report)
│       └── Button (Update Rules)
└── AiDock
    ├── AgentCard (Security Agent)
    └── EvidencePanel (security insights)
```

## Data Sources

### Security Score
```typescript
// API: GET /api/v1/admin/security/score
interface SecurityScore {
  overall_score: number;
  status: 'secure' | 'warning' | 'critical';
  last_scan: string;
  active_alerts: number;
  metrics: {
    access_control: number;
    data_protection: number;
    audit_coverage: number;
    threat_detection: number;
  };
}
```

### Security Logs
```typescript
// API: GET /api/v1/admin/security/logs
interface SecurityLogList {
  logs: SecurityLog[];
  total_count: number;
}

interface SecurityLog {
  log_id: string;
  timestamp: string;
  event: string;
  user_id: string;
  user_name: string;
  ip_address: string;
  severity: 'info' | 'warning' | 'critical';
  details?: Record<string, any>;
}
```

### Threat Detection
```typescript
// API: GET /api/v1/admin/security/threats
interface ThreatList {
  threats: Threat[];
  active_count: number;
}

interface Threat {
  threat_id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  detected_at: string;
  status: 'active' | 'investigating' | 'resolved';
  affected_resources: string[];
}
```

### React Query
```typescript
const { data: score } = useQuery({
  queryKey: ['admin', 'security', 'score'],
  queryFn: () => api.get('/api/v1/admin/security/score'),
  refetchInterval: 60_000, // 1 minute
});

const { data: logs } = useQuery({
  queryKey: ['admin', 'security', 'logs', filters],
  queryFn: () => api.get('/api/v1/admin/security/logs', { params: filters }),
});

const { data: threats } = useQuery({
  queryKey: ['admin', 'security', 'threats'],
  queryFn: () => api.get('/api/v1/admin/security/threats'),
});

const runScan = useMutation({
  mutationFn: () => api.post('/api/v1/admin/security/scan'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'security'] });
    toast.success('Security scan completed');
  },
});
```

## Zustand Store
```typescript
// stores/securityCenterStore.ts
interface SecurityCenterState {
  activeTab: string;
  autoRefresh: boolean;
  setTab: (tab: string) => void;
  setAutoRefresh: (enabled: boolean) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View security score
3. Analyze trends
4. Review metrics

### Manage Access
1. Click Access tab
2. View permissions matrix
3. Modify user access
4. Save changes

### Review Logs
1. Click Logs tab
2. Filter by severity
3. Click log for details
4. Investigate events

### Detect Threats
1. Click Threats tab
2. View active threats
3. Investigate alerts
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Score: Skeleton gauge
- Logs: Skeleton table
- Threats: Skeleton cards

## Error States
- Scan failure: Error details
- Load failure: Retry button
- Network error: Toast notification

## Accessibility
- Score announced via `aria-live`
- Threats are focusable
- Screen reader: "Security score: 85%"
- Keyboard: Enter to view details

## Telemetry
- `security_center.view` — Screen loaded
- `security_center.scan` — Scan run
- `security_center.threat_view` — Threat viewed
- `security_center.access_change` — Access modified

## Implementation Notes
- Security score gauge
- Real-time threat detection
- Access control management
- AiDock provides security insights
- Export for compliance
