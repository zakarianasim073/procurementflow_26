# TRUST-024: Incident Management Screen Specification

**Module:** `features/incident-management/IncidentManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Track, manage, and resolve system incidents and issues.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Incident Management           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ IncidentManagementHeader (open, resolved)        │
│          ├──────────────────────────────────────────────────┤
│          │ IncidentManagement (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Open] [Resolved] [Create]            │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OpenTab (active incidents)                  │   │
│          │ │ ResolvedTab (resolved incidents)            │   │
│          │ │ CreateTab (new incident)                    │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (incident insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
IncidentManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── IncidentManagementHeader
│   ├── KpiStrip (open_count, resolved_count, avg_resolution_time)
│   └── Button (Create Incident)
├── IncidentManagement
│   ├── Tabs
│   │   ├── OpenTab
│   │   │   └── IncidentList
│   │   │       └── IncidentCard × N
│   │   │           ├── title
│   │   │           ├── severity
│   │   │           ├── status
│   │   │           ├── created_at
│   │   │           └── Button (View Details)
│   │   ├── ResolvedTab
│   │   │   └── IncidentList (resolved)
│   │   └── CreateTab
│   │       └── IncidentForm
│   │           ├── title
│   │           ├── description
│   │           ├── severity
│   │           ├── assignee
│   │           └── Button (Submit)
│   ├── IncidentDetails
│   │   ├── incident_info
│   │   ├── timeline
│   │   ├── comments
│   │   └── actions
│   └── IncidentStats
│       ├── chart (incidents_over_time)
│       ├── chart (by_severity)
│       └── chart (resolution_time)
└── AiDock
    ├── AgentCard (Incident Agent)
    └── EvidencePanel (incident insights)
```

## Data Sources

### Incidents
```typescript
// API: GET /api/v1/trust/incidents
interface IncidentList {
  incidents: Incident[];
  open_count: number;
  resolved_count: number;
  avg_resolution_time: number;
}

interface Incident {
  incident_id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'investigating' | 'resolved' | 'closed';
  assignee?: string;
  created_at: string;
  resolved_at?: string;
  timeline: TimelineEntry[];
  comments: Comment[];
}

interface TimelineEntry {
  entry_id: string;
  action: string;
  user: string;
  timestamp: string;
  details?: string;
}

interface Comment {
  comment_id: string;
  user: string;
  content: string;
  timestamp: string;
}
```

### React Query
```typescript
const { data: incidents } = useQuery({
  queryKey: ['trust', 'incidents'],
  queryFn: () => api.get('/api/v1/trust/incidents'),
});

const createIncident = useMutation({
  mutationFn: (incident: CreateIncidentRequest) => api.post('/api/v1/trust/incidents', incident),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'incidents'] });
    toast.success('Incident created');
  },
});

const updateIncident = useMutation({
  mutationFn: ({ incidentId, updates }: { incidentId: string; updates: UpdateIncidentRequest }) =>
    api.patch(`/api/v1/trust/incidents/${incidentId}`, updates),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'incidents'] });
    toast.success('Incident updated');
  },
});
```

## Zustand Store
```typescript
// stores/incidentManagementStore.ts
interface IncidentManagementState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Incident
1. Click incident card
2. View details
3. Check timeline
4. Read comments

### Create Incident
1. Click Create tab
2. Fill form
3. Set severity
4. Submit incident

### Update Incident
1. View incident
2. Add comment
3. Update status
4. Assign user

### Resolve Incident
1. Click Resolve
2. Add resolution notes
3. Update status
4. Confirm resolution

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + details |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified list |

## Loading States
- Incidents: Skeleton cards
- Details: Loading spinner
- Form: Loading state

## Error States
- Create failure: Toast error
- Update failure: Toast error
- Network error: Toast notification

## Accessibility
- Incidents are focusable
- Status announced via `aria-live`
- Screen reader: "Incident: API Down, severity: critical"
- Keyboard: Tab through incidents

## Telemetry
- `incident_management.view` — Screen loaded
- `incident_management.create` — Incident created
- `incident_management.update` — Incident updated
- `incident_management.resolve` — Incident resolved

## Implementation Notes
- Incident tracking
- Timeline management
- Comment system
- AiDock provides incident insights
- Export for reporting
