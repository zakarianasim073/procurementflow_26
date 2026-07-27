# KNOW-013: Knowledge Graph Screen Specification

**Module:** `features/knowledge-graph/KnowledgeGraphPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Visual knowledge representation, entity relationships, and graph exploration.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Knowledge Graph           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ KnowledgeGraphHeader (search, filters)           │
│          ├──────────────────────────────────────────────────┤
│          │ KnowledgeGraph (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (entity search)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ GraphCanvas (interactive graph)             │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │                                          ││   │
│          │ │ │    [Entity] ---- [Entity]                 ││   │
│          │ │ │       |              |                    ││   │
│          │ │ │    [Entity] ---- [Entity]                 ││   │
│          │ │ │                                          ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ EntityPanel (selected entity details)       │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (graph insights, relationship suggestions)           │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
KnowledgeGraphPage
├── ExecutiveHeader
├── Breadcrumb
├── KnowledgeGraphHeader
│   ├── SearchBar (entity search)
│   ├── ChipSelect (entity_types)
│   ├── ChipSelect (relationship_types)
│   └── Button (Export Graph)
├── KnowledgeGraph
│   ├── GraphCanvas
│   │   ├── Node × N
│   │   │   ├── entity_type
│   │   │   ├── label
│   │   │   └── connections
│   │   └── Edge × N
│   │       ├── relationship_type
│   │       └── weight
│   ├── EntityPanel
│   │   ├── entity_info
│   │   ├── relationships
│   │   └── related_entities
│   └── GraphControls
│       ├── zoom_in/out
│       ├── fit_to_screen
│       └── toggle_labels
└── AiDock
    ├── AgentCard (Knowledge Agent)
    └── EvidencePanel (graph insights)
```

## Data Sources

### Knowledge Graph
```typescript
// API: GET /api/v1/knowledge/graph
interface KnowledgeGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface GraphNode {
  node_id: string;
  entity_type: string;
  label: string;
  properties: Record<string, any>;
  connections: number;
}

interface GraphEdge {
  edge_id: string;
  source: string;
  target: string;
  relationship_type: string;
  weight: number;
  properties?: Record<string, any>;
}
```

### Entity Details
```typescript
// API: GET /api/v1/knowledge/graph/entities/{entity_id}
interface EntityDetails {
  entity_id: string;
  entity_type: string;
  label: string;
  properties: Record<string, any>;
  relationships: EntityRelationship[];
  related_entities: RelatedEntity[];
}

interface EntityRelationship {
  relationship_id: string;
  target_entity: string;
  relationship_type: string;
  properties?: Record<string, any>;
}

interface RelatedEntity {
  entity_id: string;
  entity_type: string;
  label: string;
  relationship_type: string;
}
```

### React Query
```typescript
const { data: graph } = useQuery({
  queryKey: ['knowledge', 'graph', filters],
  queryFn: () => api.get('/api/v1/knowledge/graph', { params: filters }),
});

const { data: entity } = useQuery({
  queryKey: ['knowledge', 'graph', 'entities', entityId],
  queryFn: () => api.get(`/api/v1/knowledge/graph/entities/${entityId}`),
  enabled: !!entityId,
});
```

## Zustand Store
```typescript
// stores/knowledgeGraphStore.ts
interface KnowledgeGraphState {
  selectedNode: string | null;
  zoom: number;
  filters: {
    entity_types: string[];
    relationship_types: string[];
  };
  setSelectedNode: (id: string | null) => void;
  setZoom: (zoom: number) => void;
  setFilter: <K extends keyof KnowledgeGraphState['filters']>(key: K, value: KnowledgeGraphState['filters'][K]) => void;
}
```

## Interactions

### Select Node
1. Click node
2. Highlight node
3. Show connections
4. Open EntityPanel

### Zoom Graph
1. Scroll to zoom
2. Adjust view
3. Preserve selection
4. Update controls

### Filter Graph
1. Apply filter
2. Update nodes/edges
3. Preserve layout
4. Refresh canvas

### Search Entity
1. Type in search bar
2. Find matching nodes
3. Highlight results
4. Navigate to entity

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full graph + panel |
| Tablet (768-1024px) | Graph + collapsible panel |
| Mobile (<768px) | Simplified graph, bottom panel |

## Loading States
- Graph: Loading canvas
- Entity: Skeleton panel
- Search: Loading spinner

## Error States
- Load failure: Retry button
- No data: EmptyState
- Network error: Toast notification

## Accessibility
- Nodes are focusable
- Selection announced via `aria-live`
- Screen reader: "Entity X, 5 connections"
- Keyboard: Arrow keys to navigate, Enter to select

## Telemetry
- `knowledge_graph.view` — Screen loaded
- `knowledge_graph.node_select` — Node selected
- `knowledge_graph.search` — Search performed
- `knowledge_graph.export` — Graph exported

## Implementation Notes
- Interactive graph visualization
- Node/edge filtering
- Entity detail panel
- AiDock provides graph insights
- Export for analysis
