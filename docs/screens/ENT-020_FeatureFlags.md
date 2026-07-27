# ENT-020: Feature Flags Screen Specification

**Module:** `features/feature-flags/FeatureFlagsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Manage feature flags, toggles, and feature rollouts.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Feature Flags              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ FeatureFlagsHeader (flags, active)               │
│          ├──────────────────────────────────────────────────┤
│          │ FeatureFlags (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (flag search)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FlagList (feature flags)                    │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Feature: Dark Mode    [ON]              ││   │
│          │ │ │ Feature: New Pricing  [OFF]             ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FlagDetails (selected flag)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (flag insights)                                      │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
FeatureFlagsPage
├── ExecutiveHeader
├── Breadcrumb
├── FeatureFlagsHeader
│   ├── KpiStrip (flag_count, active_count)
│   └── Button (Create Flag)
├── FeatureFlags
│   ├── FlagFilters
│   │   ├── SearchBar
│   │   ├── ChipSelect (status)
│   │   └── ChipSelect (environment)
│   ├── FlagList
│   │   └── VirtualList<FeatureFlag>
│   │       └── FlagCard × N
│   │           ├── name
│   │           ├── description
│   │           ├── status (toggle)
│   │           ├── environment
│   │           └── Button (Edit)
│   └── FlagDetails
│       ├── flag_info
│       ├── targeting_rules
│       ├── percentage_rollout
│       └── metrics
└── AiDock
    ├── AgentCard (Feature Agent)
    └── EvidencePanel (flag insights)
```

## Data Sources

### Feature Flags
```typescript
// API: GET /api/v1/admin/feature-flags
interface FeatureFlagList {
  flags: FeatureFlag[];
  total_count: number;
  active_count: number;
}

interface FeatureFlag {
  flag_id: string;
  name: string;
  description: string;
  enabled: boolean;
  environment: string;
  targeting_rules: TargetingRule[];
  percentage_rollout: number;
  created_at: string;
  updated_at: string;
}

interface TargetingRule {
  rule_id: string;
  attribute: string;
  operator: string;
  value: string;
}
```

### React Query
```typescript
const { data: flags } = useQuery({
  queryKey: ['admin', 'feature-flags'],
  queryFn: () => api.get('/api/v1/admin/feature-flags'),
});

const toggleFlag = useMutation({
  mutationFn: ({ flagId, enabled }: { flagId: string; enabled: boolean }) =>
    api.patch(`/api/v1/admin/feature-flags/${flagId}`, { enabled }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'feature-flags'] });
    toast.success('Flag updated');
  },
});

const createFlag = useMutation({
  mutationFn: (flag: CreateFlagRequest) => api.post('/api/v1/admin/feature-flags', flag),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'feature-flags'] });
    toast.success('Flag created');
  },
});
```

## Zustand Store
```typescript
// stores/featureFlagsStore.ts
interface FeatureFlagsState {
  selectedFlag: string | null;
  filters: {
    search: string;
    status: string[];
    environment: string[];
  };
  setFlag: (id: string | null) => void;
  setFilter: <K extends keyof FeatureFlagsState['filters']>(key: K, value: FeatureFlagsState['filters'][K]) => void;
}
```

## Interactions

### Toggle Flag
1. Click toggle switch
2. Update flag status
3. Confirm change
4. Refresh list

### Create Flag
1. Click Create button
2. Fill flag details
3. Set targeting rules
4. Save flag

### Edit Flag
1. Click Edit button
2. Modify settings
3. Update rules
4. Save changes

### View Metrics
1. Click flag card
2. View details
3. Check metrics
4. Analyze impact

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full list + details |
| Tablet (768-1024px) | List with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Flags: Skeleton cards
- Details: Loading spinner
- Toggle: Loading state

## Error States
- Toggle failure: Toast error
- Create failure: Toast error
- Network error: Toast notification

## Accessibility
- Toggles are focusable
- Status changes announced via `aria-live`
- Screen reader: "Feature Dark Mode, enabled"
- Keyboard: Tab through flags, Space to toggle

## Telemetry
- `feature_flags.view` — Screen loaded
- `feature_flags.toggle` — Flag toggled
- `feature_flags.create` — Flag created
- `feature_flags.edit` — Flag edited

## Implementation Notes
- Real-time flag toggling
- Targeting rules engine
- Percentage rollouts
- AiDock provides flag insights
- A/B testing support
