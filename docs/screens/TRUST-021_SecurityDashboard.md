# TRUST-021: Security Dashboard Screen Specification

**Module:** `features/security-dashboard/SecurityDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Comprehensive security monitoring, threat detection, and incident response.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Security Dashboard            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SecurityDashboardHeader (score, threats)         │
│          ├──────────────────────────────────────────────────┤
│          │ SecurityDashboard (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SecurityScore (overall score)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Threats] [Incidents]      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (security metrics)              │   │
│          │ │ ThreatsTab (threat detection)               │   │
│          │ │ IncidentsTab (incident management)          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (security insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SecurityDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── SecurityDashboardHeader
│   ├── KpiStrip (security_score, threats_count, incidents_count)
│   └── Button (Run Scan)
├── SecurityDashboard
│   ├── SecurityScore
│   │   ├── score_gauge
│   │   ├── score_history
│   │   └── score_breakdown
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── Chart (security_trend)
│   │   │   ├── Chart (threats_by_type)
│   │   │   └── Chart (incidents_timeline)
│   │   ├── ThreatsTab
│   │   │   └── ThreatList
│   │   │       └── ThreatCard × N
│   │   │           ├── type
│   │   │           ├── severity
│   │   │           ├── source
│   │   │           └── Button (Investigate)
│   │   └── IncidentsTab
│   │       └── IncidentList
│   │           └── IncidentCard × N
│   │               ├── title
│   │               ├── status
│   │               ├── severity
│   │               └── Button (View Details)
│   └── SecurityReport
│       ├── summary
│       ├── findings
│       └── recommendations
└── AiDock
    ├── AgentCard (Security Agent)
    └── EvidencePanel (security insights)
```

## Data Sources

### Security Data
```typescript
// API: GET /api/v1/trust/security/dashboard
interface SecurityData {
  score: number;
  threats: Threat[];
  incidents: Incident[];
  report: SecurityReport;
}

interface Threat {
  threat_id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  source: string;
  description: string;
  detected_at: string;
  status: 'active' | 'investigating' | 'mitigated';
}

interface Incident {
  incident_id: string;
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'investigating' | 'resolved';
  created_at: string;
  resolved_at?: string;
  description: string;
}
```

### React Query
```typescript
const { data: security } = useQuery({
  queryKey: ['trust', 'security', 'dashboard'],
  queryFn: () => api.get('/api/v1/trust/security/dashboard'),
});

const runScan = useMutation({
  mutationFn: () => api.post('/api/v1/trust/security/scan'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'security', 'dashboard'] });
    toast.success('Security scan completed');
  },
});

const investigateThreat = useMutation({
  mutationFn: (threatId: string) => api.post(`/api/v1/trust/security/threats/${threatId}/investigate`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'security', 'dashboard'] });
    toast.success('Investigation started');
  },
});
```

## Zustand Store
```typescript
// stores/securityDashboardStore.ts
interface SecurityDashboardState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### Run Scan
1. Click Run Scan
2. Execute scan
3. Display results
4. Update score

### View Threats
1. Click Threats tab
2. View threat list
3. Check severity
4. Investigate threat

### View Incidents
1. Click Incidents tab
2. View incident list
3. Check status
4. View details

### Generate Report
1. Click Generate Report
2. Compile findings
3. Create recommendations
4. Export report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Security: Loading score
- Threats: Loading list
- Incidents: Loading list

## Error States
- Scan failure: Retry button
- Investigation failure: Error details
- Network error: Toast notification

## Accessibility
- Threats are focusable
- Score announced via `aria-live`
- Screen reader: "Security score: 85/100"
- Keyboard: Tab through threats

## Telemetry
- `security_dashboard.view` — Screen loaded
- `security_dashboard.scan` — Scan run
- `security_dashboard.investigate` — Investigation started
- `security_dashboard.report` — Report generated

## Implementation Notes
- Security scoring
- Threat detection
- Incident management
- AiDock provides security insights
- Report generation
