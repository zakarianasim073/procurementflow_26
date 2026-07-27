# TEN-013: Risk Assessment Screen Specification

**Module:** `features/risk-assessment/RiskAssessmentPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Tender risk analysis, mitigation planning, and risk monitoring.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Risk Assessment         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ RiskAssessmentHeader (tender context, score)     │
│          ├──────────────────────────────────────────────────┤
│          │ RiskAssessment (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ RiskScore (overall gauge)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Risks] [Mitigation] [Monitoring]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RiskMatrix (heatmap)                        │   │
│          │ │ RiskList (risk cards)                       │   │
│          │ │ MitigationPlan (action items)               │   │
│          │ │ MonitoringDashboard (status tracking)       │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (risk insights, mitigation suggestions)              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
RiskAssessmentPage
├── ExecutiveHeader
├── Breadcrumb
├── RiskAssessmentHeader
│   ├── TenderCard (compact)
│   ├── Gauge (risk_score)
│   └── Badge (risk_level: low/medium/high)
├── RiskAssessment
│   ├── RiskScore
│   │   └── Gauge (overall_risk)
│   ├── Tabs
│   │   ├── RisksTab
│   │   │   ├── RiskMatrix
│   │   │   │   └── Heatmap (likelihood vs impact)
│   │   │   └── RiskList
│   │   │       └── RiskCard × N
│   │   │           ├── name
│   │   │           ├── category
│   │   │           ├── likelihood
│   │   │           ├── impact
│   │   │           └── status
│   │   ├── MitigationTab
│   │   │   └── MitigationPlan
│   │   │       └── MitigationItem × N
│   │   │           ├── risk
│   │   │           ├── action
│   │   │           ├── owner
│   │   │           ├── deadline
│   │   │           └── status
│   │   └── MonitoringTab
│   │       └── MonitoringDashboard
│   │           ├── Chart (risk_trend)
│   │           ├── Table (risk_log)
│   │           └── AlertList (active_alerts)
│   └── RiskActions
│       ├── Button (Add Risk)
│       ├── Button (Update Status)
│       └── Button (Export Report)
└── AiDock
    ├── AgentCard (Risk Agent)
    └── EvidencePanel (risk insights)
```

## Data Sources

### Risk Assessment
```typescript
// API: GET /api/v1/boq/{tender_id}/risks
interface RiskAssessment {
  tender_id: string;
  overall_risk: number;
  risk_level: 'low' | 'medium' | 'high';
  risks: Risk[];
  mitigations: Mitigation[];
}

interface Risk {
  risk_id: string;
  name: string;
  category: string;
  description: string;
  likelihood: number;
  impact: number;
  risk_score: number;
  status: 'identified' | 'assessed' | 'mitigated' | 'closed';
  owner?: string;
  mitigation?: string;
}

interface Mitigation {
  mitigation_id: string;
  risk_id: string;
  action: string;
  owner: string;
  deadline: string;
  status: 'planned' | 'in_progress' | 'completed';
  progress: number;
}
```

### React Query
```typescript
const { data: assessment } = useQuery({
  queryKey: ['boq', tenderId, 'risks'],
  queryFn: () => api.get(`/api/v1/boq/${tenderId}/risks`),
});

const addRisk = useMutation({
  mutationFn: (request: AddRiskRequest) => api.post(`/api/v1/boq/${tenderId}/risks`, request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['boq', tenderId, 'risks'] });
    toast.success('Risk added');
  },
});

const updateMitigation = useMutation({
  mutationFn: ({ mitigationId, updates }: { mitigationId: string; updates: Partial<Mitigation> }) =>
    api.patch(`/api/v1/boq/${tenderId}/mitigations/${mitigationId}`, updates),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['boq', tenderId, 'risks'] });
    toast.success('Mitigation updated');
  },
});
```

## Zustand Store
```typescript
// stores/riskAssessmentStore.ts
interface RiskAssessmentState {
  activeTab: string;
  selectedRisk: string | null;
  setTab: (tab: string) => void;
  setRisk: (id: string | null) => void;
}
```

## Interactions

### View Risk Matrix
1. Click Risks tab
2. View heatmap
3. Analyze risk distribution
4. Click cell for details

### Add Risk
1. Click "Add Risk"
2. Fill risk form
3. Set likelihood/impact
4. Save risk

### Update Mitigation
1. Click mitigation item
2. Update status
3. Add progress
4. Save changes

### Monitor Risks
1. Click Monitoring tab
2. View risk trend
3. Check alerts
4. Review log

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with matrix |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Score: Skeleton gauge
- Risks: Skeleton cards
- Matrix: Skeleton heatmap

## Error States
- Load failure: Retry button
- Add failure: Toast error
- Network error: Toast notification

## Accessibility
- Risk cards are focusable
- Score announced via `aria-live`
- Screen reader: "Risk score: 75, high"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `risk_assessment.view` — Screen loaded
- `risk_assessment.add_risk` — Risk added
- `risk_assessment.update_mitigation` — Mitigation updated
- `risk_assessment.export` — Report exported

## Implementation Notes
- Risk matrix for visualization
- Risk list with details
- Mitigation tracking
- AiDock provides risk insights
- Export for reporting
