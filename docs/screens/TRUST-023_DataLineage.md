# TRUST-023: Data Lineage Screen Specification

**Module:** `features/data-lineage/DataLineagePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Track data flow, transformations, and lineage across systems.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Data Lineage                  │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DataLineageHeader (sources, transformations)     │
│          ├──────────────────────────────────────────────────┤
│          │ DataLineage (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ LineageGraph (visual flow)                  │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ [Source] → [Transform] → [Target]        ││   │
│          │ │ │                                          ││   │
│          │ │ │ [Source] → [Transform] → [Target]        ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ NodeDetails (selected node)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (lineage insights)                                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DataLineagePage
├── ExecutiveHeader
├── Breadcrumb
├── DataLineageHeader
│   ├── KpiStrip (source_count, transformation_count, target_count)
│   └── Button (Export Lineage)
├── DataLineage
│   ├── LineageGraph
│   │   ├── Node × N
│   │   │   ├── type (source, transform, target)
│   │   │   ├── name
│   │   │   ├── connections
│   │   │   └── status
│   │   └── Edge × N
│   │       ├── source
│   │       ├── target
│   │       └── transformation
│   ├── NodeDetails
│   │   ├── node_info
│   │   ├── input/output
│   │   ├── transformations
│   │   └── quality_metrics
│   ├── LineageSearch
│   │   ├── SearchBar
│   │   └── SearchResults
│   │       └── ResultCard × N
│   └── LineageStats
│       ├── chart (flow_distribution)
│       ├── chart (quality_by_node)
│       └── chart (transformation_types)
└── AiDock
    ├── AgentCard (Data Agent)
    └── EvidencePanel (lineage insights)
```

## Data Sources

### Data Lineage
```typescript
// API: GET /api/v1/trust/lineage
interface DataLineage {
  nodes: LineageNode[];
  edges: LineageEdge[];
  stats: LineageStats;
}

interface LineageNode {
  node_id: string;
  name: string;
  type: 'source' | 'transformation' | 'target';
  system: string;
  connections: string[];
  quality_score: number;
  last_updated: string;
}

interface LineageEdge {
  edge_id: string;
  source_id: string;
  target_id: string;
  transformation: string;
  frequency: string;
}

interface LineageStats {
  total_nodes: number;
  total_edges: number;
  avg_quality_score: number;
  transformation_types: { type: string; count: number }[];
}
```

### React Query
```typescript
const { data: lineage } = useQuery({
  queryKey: ['trust', 'lineage'],
  queryFn: () => api.get('/api/v1/trust/lineage'),
});
```

## Zustand Store
```typescript
// stores/dataLineageStore.ts
interface DataLineageState {
  selectedNode: string | null;
  searchQuery: string;
  setNode: (id: string | null) => void;
  setSearch: (query: string) => void;
}
```

## Interactions

### View Node
1. Click node
2. View details
3. Check connections
4. Review quality

### Search Lineage
1. Type query
2. Search nodes
3. View results
4. Navigate to node

### Trace Flow
1. Select source node
2. Follow edges
3. View transformations
4. Check targets

### Export Lineage
1. Click Export
2. Choose format
3. Include all nodes
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full graph + details |
| Tablet (768-1024px) | Graph with modal details |
| Mobile (<768px) | Simplified view |

## Loading States
- Graph: Loading canvas
- Details: Loading spinner
- Search: Loading results

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Nodes are focusable
- Connections announced via `aria-live`
- Screen reader: "Node: SOR Data, connected to 3 targets"
- Keyboard: Arrow keys to navigate

## Telemetry
- `data_lineage.view` — Screen loaded
- `data_lineage.node_select` — Node selected
- `data_lineage.search` — Search performed
- `data_lineage.export` — Lineage exported

## Implementation Notes
- Visual lineage graph
- Node/edge filtering
- Quality tracking
- AiDock provides lineage insights
- Export for documentation
