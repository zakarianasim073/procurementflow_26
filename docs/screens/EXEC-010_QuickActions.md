# EXEC-010: Quick Actions Screen Specification

**Module:** `features/quick-actions/QuickActionsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Common task shortcuts, bulk operations, and productivity tools.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Quick Actions             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ QuickActionsHeader (recent, favorites)           │
│          ├──────────────────────────────────────────────────┤
│          │ QuickActions (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (action search)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ActionGrid (categorized actions)            │   │
│          │ │ ┌──────────────┐ ┌──────────────┐          │   │
│          │ │ │ Tender       │ │ Bulk         │          │   │
│          │ │ │ Actions      │ │ Operations   │          │   │
│          │ │ │ • Create     │ │ • Import     │          │   │
│          │ │ │ • Import     │ │ • Export     │          │   │
│          │ │ │ • Analyze    │ │ • Sync       │          │   │
│          │ │ └──────────────┘ └──────────────┘          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RecentActions (recently used)               │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (action suggestions, productivity)                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
QuickActionsPage
├── ExecutiveHeader
├── Breadcrumb
├── QuickActionsHeader
│   ├── KpiStrip (total_actions, recent_count, favorite_count)
│   └── Button (Customize)
├── QuickActions
│   ├── SearchBar (action search)
│   ├── ActionGrid
│   │   └── ActionCategory × N
│   │       ├── category_name
│   │       └── ActionCard × N
│   │           ├── icon
│   │           ├── name
│   │           ├── description
│   │           └── Button (Execute)
│   ├── RecentActions
│   │   └── ActionCard × N
│   │       ├── icon
│   │       ├── name
│   │       ├── last_used
│   │       └── Button (Execute)
│   └── FavoriteActions
│       └── ActionCard × N
│           ├── icon
│           ├── name
│           └── Button (Execute)
└── AiDock
    ├── AgentCard (Productivity Agent)
    └── EvidencePanel (action suggestions)
```

## Data Sources

### Quick Actions
```typescript
// API: GET /api/v1/actions
interface ActionList {
  categories: ActionCategory[];
  recent: Action[];
  favorites: Action[];
}

interface ActionCategory {
  category_id: string;
  name: string;
  description: string;
  actions: Action[];
}

interface Action {
  action_id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  shortcut?: string;
  last_used?: string;
  use_count: number;
}
```

### React Query
```typescript
const { data: actions } = useQuery({
  queryKey: ['actions'],
  queryFn: () => api.get('/api/v1/actions'),
});

const executeAction = useMutation({
  mutationFn: (actionId: string) => api.post(`/api/v1/actions/${actionId}/execute`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['actions'] });
    toast.success('Action executed');
  },
});

const toggleFavorite = useMutation({
  mutationFn: ({ actionId, favorite }: { actionId: string; favorite: boolean }) =>
    api.patch(`/api/v1/actions/${actionId}`, { favorite }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['actions'] });
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
1. Type in search bar
2. Debounce 300ms
3. Filter actions
4. Update grid

### Execute Action
1. Click action card
2. Execute action
3. Show progress
4. Show result

### Toggle Favorite
1. Click star icon
2. Toggle favorite
3. Update list
4. Show confirmation

### Customize Actions
1. Click Customize button
2. Reorder actions
3. Hide unused actions
4. Save preferences

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Grid with categories |
| Tablet (768-1024px) | Stacked categories |
| Mobile (<768px) | List view |

## Loading States
- Actions: Skeleton cards
- Execute: Spinner on card
- Search: Loading spinner

## Error States
- Execute failure: Toast error
- Load failure: Retry button
- Network error: Toast notification

## Accessibility
- Action cards are focusable
- Execution announced via `aria-live`
- Screen reader: "Action X, recently used"
- Keyboard: Enter to execute, Space to favorite

## Telemetry
- `quick_actions.view` — Screen loaded
- `quick_actions.execute` — Action executed
- `quick_actions.favorite` — Favorite toggled
- `quick_actions.search` — Search performed

## Implementation Notes
- Searchable action grid
- Recent and favorite actions
- Shortcut support
- AiDock provides action suggestions
- Customization for productivity
