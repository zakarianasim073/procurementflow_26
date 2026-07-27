# ENT-024: Plugin Manager Screen Specification

**Module:** `features/plugin-manager/PluginManagerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Manage system plugins, extensions, and add-ons.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Plugin Manager             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ PluginManagerHeader (plugins, active)            │
│          ├──────────────────────────────────────────────────┤
│          │ PluginManager (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (plugin search)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ PluginGrid (available plugins)              │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │Plugin│Plugin│Plugin│Plugin│              │   │
│          │ │ │  A   │  B   │  C   │  D   │              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ PluginDetails (selected plugin)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (plugin recommendations)                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
PluginManagerPage
├── ExecutiveHeader
├── Breadcrumb
├── PluginManagerHeader
│   ├── KpiStrip (plugin_count, active_count)
│   └── Button (Install Plugin)
├── PluginManager
│   ├── SearchBar
│   │   └── SearchInput
│   ├── PluginGrid
│   │   └── PluginCard × N
│   │       ├── icon
│   │       ├── name
│   │       ├── description
│   │       ├── version
│   │       ├── status
│   │       └── Button (Install/Update/Remove)
│   ├── PluginDetails
│   │   ├── plugin_info
│   │   ├── configuration
│   │   ├── dependencies
│   │   └── Button (Configure)
│   ├── InstalledPlugins
│   │   └── InstalledCard × N
│   │       ├── name
│   │       ├── version
│   │       ├── status
│   │       └── actions (update, remove)
│   └── PluginLogs
│       └── LogEntry × N
│           ├── timestamp
│           ├── event
│           └── status
└── AiDock
    ├── AgentCard (Plugin Agent)
    └── EvidencePanel (plugin recommendations)
```

## Data Sources

### Plugins
```typescript
// API: GET /api/v1/admin/plugins
interface PluginList {
  plugins: Plugin[];
  installed: Plugin[];
  total_count: number;
  active_count: number;
}

interface Plugin {
  plugin_id: string;
  name: string;
  description: string;
  version: string;
  author: string;
  icon: string;
  status: 'available' | 'installed' | 'active' | 'inactive';
  dependencies: string[];
  configuration?: Record<string, any>;
}
```

### React Query
```typescript
const { data: plugins } = useQuery({
  queryKey: ['admin', 'plugins'],
  queryFn: () => api.get('/api/v1/admin/plugins'),
});

const installPlugin = useMutation({
  mutationFn: (pluginId: string) => api.post(`/api/v1/admin/plugins/${pluginId}/install`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'plugins'] });
    toast.success('Plugin installed');
  },
});

const removePlugin = useMutation({
  mutationFn: (pluginId: string) => api.delete(`/api/v1/admin/plugins/${pluginId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'plugins'] });
    toast.success('Plugin removed');
  },
});
```

## Zustand Store
```typescript
// stores/pluginManagerStore.ts
interface PluginManagerState {
  selectedPlugin: string | null;
  searchQuery: string;
  setPlugin: (id: string | null) => void;
  setSearch: (query: string) => void;
}
```

## Interactions

### Search Plugins
1. Type query
2. Search plugins
3. View results
4. Select plugin

### Install Plugin
1. Click Install button
2. Confirm installation
3. Install plugin
4. Update status

### Configure Plugin
1. Click Configure button
2. View settings
3. Modify configuration
4. Save changes

### Remove Plugin
1. Click Remove button
2. Confirm removal
3. Uninstall plugin
4. Update grid

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + details |
| Tablet (768-1024px) | Grid with modal details |
| Mobile (<768px) | Simplified grid |

## Loading States
- Plugins: Skeleton cards
- Details: Loading spinner
- Install: Progress indicator

## Error States
- Install failure: Toast error
- Remove failure: Toast error
- Network error: Toast notification

## Accessibility
- Plugins are focusable
- Status announced via `aria-live`
- Screen reader: "Plugin: Analytics, status: active"
- Keyboard: Tab through plugins

## Telemetry
- `plugin_manager.view` — Screen loaded
- `plugin_manager.search` — Search performed
- `plugin_manager.install` — Plugin installed
- `plugin_manager.remove` — Plugin removed
- `plugin_manager.configure` — Plugin configured

## Implementation Notes
- Plugin marketplace
- Installation management
- Configuration system
- AiDock provides plugin recommendations
- Dependency management
