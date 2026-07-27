# KNOW-014: Relationship Explorer Screen Specification

**Module:** `features/relationship-explorer/RelationshipExplorerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Explore and analyze relationships between entities, contractors, and tenders.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Relationship Explorer    │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ RelationshipExplorerHeader (search, filters)    │
│          ├──────────────────────────────────────────────────┤
│          │ RelationshipExplorer (main content)             │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (entity search)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RelationshipGraph (visual)                  │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │                                          ││   │
│          │ │ │    [Entity A] ── [Entity B]               ││   │
│          │ │ │         │                                ││   │
│          │ │ │    [Entity C]                            ││   │
│          │ │ │                                          ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ EntityDetails (selected entity)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (relationship insights)                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
RelationshipExplorerPage
├── ExecutiveHeader
├── Breadcrumb
├── RelationshipExplorerHeader
│   ├── SearchBar (entity search)
│   ├── ChipSelect (entity_types)
│   ├── ChipSelect (relationship_types)
│   └── Button (Export)
├── RelationshipExplorer
│   ├── SearchPanel
│   │   ├── SearchBar
│   │   └── SearchResults
│   │       └── EntityCard × N
│   ├── RelationshipGraph
│   │   ├── Node × N
│   │   └── Edge × N
│   ├── EntityDetails
│   │   ├── entity_info
│   │   ├── relationships
│   │   └── connected_entities
│   └── RelationshipHistory
│       └── HistoryEntry × N
│           ├── date
│           ├── event
│           └── details
└── AiDock
    ├── AgentCard (Knowledge Agent)
    └── EvidencePanel (relationship insights)
```

## Data Sources

### Entity Relationships
```typescript
// API: GET /api/v1/knowledge/relationships
interface RelationshipData {
  entities: Entity[];
  relationships: Relationship[];
}

interface Entity {
  entity_id: string;
  entity_type: string;
  name: string;
  properties: Record<string, any>;
}

interface Relationship {
  source: string;
  target: string;
  type: string;
  strength: number;
  created_at: string;
}
```

### React Query
```typescript
const { data: relationships } = useQuery({
  queryKey: ['knowledge', 'relationships', filters],
  queryFn: () => api.get('/api/v1/knowledge/relationships', { params: filters }),
});

const { data: entityDetails } = useQuery({
  queryKey: ['knowledge', 'relationships', 'entity', entityId],
  queryFn: () => api.get(`/api/v1/knowledge/relationships/${entityId}`),
  enabled: !!entityId,
});
```

## Zustand Store
```typescript
// stores/relationshipExplorerStore.ts
interface RelationshipExplorerState {
  selectedEntity: string | null;
  filters: {
    entity_types: string[];
    relationship_types: string[];
  };
  setEntity: (id: string | null) => void;
  setFilter: <K extends keyof RelationshipExplorerState['filters']>(key: K, value: RelationshipExplorerState['filters'][K]) => void;
}
```

## Interactions

### Search Entity
1. Type in search bar
2. Find matching entities
3. Select entity
4. View relationships

### View Relationship
1. Click edge
2. View relationship details
3. See connected entities
4. Analyze strength

### Filter Relationships
1. Apply filter
2. Update graph
3. Preserve selection
4. Refresh display

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full graph + details |
| Tablet (768-1024px) | Graph + collapsible details |
| Mobile (<768px) | List view |

## Loading States
- Graph: Loading canvas
- Details: Skeleton panel
- Search: Loading spinner

## Error States
- Load failure: Retry button
- No data: EmptyState
- Network error: Toast notification

## Accessibility
- Nodes are focusable
- Relationships announced via `aria-live`
- Screen reader: "Entity A connected to Entity B"
- Keyboard: Arrow keys to navigate

## Telemetry
- `relationship_explorer.view` — Screen loaded
- `relationship_explorer.search` — Search performed
- `relationship_explorer.select` — Entity selected
- `relationship_explorer.export` — Relationships exported

## Implementation Notes
- Interactive relationship graph
- Entity search and selection
- Relationship strength visualization
- AiDock provides relationship insights
- Export for analysis
