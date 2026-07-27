# EXEC-019: Quick Actions Screen Specification

**Module:** `features/quick-actions/QuickActionsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Quick access to common actions, shortcuts, and workflows.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Quick Actions             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ QuickActionsHeader (shortcuts, recent)           │
│          ├──────────────────────────────────────────────────┤
│          │ QuickActions (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (action search)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ActionGrid (action cards)                   │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │New   │Upload│Search│Export│              │   │
│          │ │ │Tender│BOQ   │      │Report│              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RecentActions (recently used)               │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (action suggestions)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
QuickActionsPage
├── ExecutiveHeader
├── Breadcrumb
├── QuickActionsHeader
│   ├── KpiStrip (shortcut_count, recent_count)
│   └── Button (Customize)
├── QuickActions
│   ├── SearchBar
│   │   └── SearchInput
│   ├── ActionGrid
│   │   └── ActionCard × N
│   │       ├── icon
│   │       ├── name
│   │       ├── description
│   │       ├── shortcut
│   │       └── Button (Execute)
│   ├── RecentActions
│   │   └── RecentCard × N
│   │       ├── action_name
│   │       ├── last_used
│   │       └── Button (Execute)
│   ├── ActionCategories
│   │   └── Category × N
│   │       ├── name
│   │       ├── actions_count
│   │       └── ActionItem × N
│   └── CustomShortcuts
│       └── Shortcut × N
│           ├── action
│           ├── key_combination
│           └── Button (Edit)
└── AiDock
    ├── AgentCard (Assistant Agent)
    └── EvidencePanel (action suggestions)
```

## Data Sources

### Quick Actions
```typescript
// API: GET /api/v1/actions/quick
interface QuickActions {
  actions: Action[];
  recent: RecentAction[];
  categories: ActionCategory[];
}

interface Action {
  action_id: string;
  name: string;
  description: string;
  icon: string;
  shortcut?: string;
  category: string;
  enabled: boolean;
}

interface RecentAction {
  action_id: string;
  action_name: string;
  last_used: string;
  usage_count: number;
}

interface ActionCategory {
  category_id: string;
  name: string;
  actions_count: number;
  actions: Action[];
}
```

### React Query
```typescript
const { data: actions } = useQuery({
  queryKey: ['actions', 'quick'],
  queryFn: () => api.get('/api/v1/actions/quick'),
});

const executeAction = useMutation({
  mutationFn: (actionId: string) => api.post(`/api/v1/actions/quick/${actionId}/execute`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['actions', 'quick'] });
    toast.success('Action executed');
  },
});
```

## Zustand Store
```typescript
// stores/quickActionsStore.ts
interface QuickActionsState {
  searchQuery: string;
  setSearch: (query: string) => void;
}
```

## Interactions

### Search Actions
1. Type query
2. Filter actions
3. View results
4. Execute action

### Execute Action
1. Click action card
2. Confirm execution
3. Run action
4. Update recent

### Customize Shortcuts
1. Click Customize
2. Edit shortcuts
3. Save changes
4. Update grid

### View Recent
1. View recent list
2. Click action
3. Execute action
4. Update usage

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + recent |
| Tablet (768-1024px) | Stacked grid |
| Mobile (<768px) | Simplified list |

## Loading States
- Actions: Skeleton grid
- Recent: Skeleton cards
- Search: Loading spinner

## Error States
- Execute failure: Toast error
- Save failure: Toast error
- Network error: Toast notification

## Accessibility
- Actions are focusable
- Execution announced via `aria-live`
- Screen reader: "Action: New Tender, shortcut: Ctrl+N"
- Keyboard: Tab through actions

## Telemetry
- `quick_actions.view` — Screen loaded
- `quick_actions.search` — Search performed
- `quick_actions.execute` — Action executed
- `quick_actions.customize` — Shortcuts customized

## Implementation Notes
- Action search
- Keyboard shortcuts
- Recent actions
- AiDock provides action suggestions
- Custom shortcuts
