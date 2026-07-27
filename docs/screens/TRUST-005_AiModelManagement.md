# TRUST-005: AI Model Management Screen Specification

**Module:** `features/ai-models/AiModelManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
AI model configuration, performance monitoring, version management, and model deployment.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > AI Model Management           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AiModelHeader (active model, status)             │
│          ├──────────────────────────────────────────────────┤
│          │ AiModelManagement (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Models] [Performance] [Config]      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ModelList (model cards)                     │   │
│          │ │ PerformanceMetrics (charts)                 │   │
│          │ │ ConfigurationForm (settings)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (model insights, optimization suggestions)           │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AiModelManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── AiModelHeader
│   ├── Badge (active_model)
│   ├── KpiStrip (accuracy, latency, cost)
│   └── Button (Deploy New Model)
├── AiModelManagement
│   ├── Tabs
│   │   ├── ModelsTab
│   │   │   └── ModelList
│   │   │       └── ModelCard × N
│   │   │           ├── name
│   │   │           ├── version
│   │   │           ├── status (active/inactive)
│   │   │           ├── accuracy
│   │   │           └── Button (Deploy/Deactivate)
│   │   ├── PerformanceTab
│   │   │   └── PerformanceMetrics
│   │   │       ├── Chart (accuracy over time)
│   │   │       ├── Chart (latency over time)
│   │   │       └── Chart (cost over time)
│   │   └── ConfigTab
│   │       └── ConfigurationForm
│   │           ├── Input (api_key)
│   │           ├── Input (model_name)
│   │           ├── Input (temperature)
│   │           ├── Input (max_tokens)
│   │           └── Button (Save)
│   └── ModelDetail
│       ├── metrics
│       ├── training_data
│       └── deployment_history
└── AiDock
    ├── AgentCard (AI Agent)
    └── EvidencePanel (model insights)
```

## Data Sources

### AI Models
```typescript
// API: GET /api/v1/ai/models
interface AiModelList {
  models: AiModel[];
  active_model: string;
}

interface AiModel {
  model_id: string;
  name: string;
  version: string;
  provider: string;
  status: 'active' | 'inactive' | 'training';
  accuracy: number;
  latency: number;
  cost_per_1k_tokens: number;
  created_at: string;
  deployed_at?: string;
}
```

### Performance Metrics
```typescript
// API: GET /api/v1/ai/models/performance
interface ModelPerformance {
  accuracy_trend: { date: string; value: number }[];
  latency_trend: { date: string; value: number }[];
  cost_trend: { date: string; value: number }[];
  usage_stats: {
    total_requests: number;
    total_tokens: number;
    avg_tokens_per_request: number;
  };
}
```

### React Query
```typescript
const { data: models } = useQuery({
  queryKey: ['ai', 'models'],
  queryFn: () => api.get('/api/v1/ai/models'),
});

const { data: performance } = useQuery({
  queryKey: ['ai', 'models', 'performance'],
  queryFn: () => api.get('/api/v1/ai/models/performance'),
});

const deployModel = useMutation({
  mutationFn: (modelId: string) => api.post(`/api/v1/ai/models/${modelId}/deploy`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['ai', 'models'] });
    toast.success('Model deployed');
  },
});

const deactivateModel = useMutation({
  mutationFn: (modelId: string) => api.post(`/api/v1/ai/models/${modelId}/deactivate`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['ai', 'models'] });
    toast.success('Model deactivated');
  },
});
```

## Zustand Store
```typescript
// stores/aiModelManagementStore.ts
interface AiModelManagementState {
  activeTab: string;
  selectedModel: string | null;
  setTab: (tab: string) => void;
  setModel: (id: string | null) => void;
}
```

## Interactions

### Deploy Model
1. Click "Deploy" button
2. Confirm deployment
3. Show progress
4. Update model status

### View Performance
1. Click Performance tab
2. View charts
3. Analyze trends
4. Export metrics

### Update Configuration
1. Edit config fields
2. Save changes
3. Test configuration
4. Apply to active model

### Deactivate Model
1. Click "Deactivate" button
2. Confirm deactivation
3. Switch to fallback model
4. Update status

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Models: Skeleton cards
- Performance: Skeleton charts
- Config: Skeleton form

## Error States
- Deploy failure: Toast error
- Performance error: Retry button
- Network error: Toast notification

## Accessibility
- Model cards are focusable
- Status changes announced via `aria-live`
- Screen reader: "Model X, accuracy 95%"
- Keyboard: Enter to select, Space to deploy

## Telemetry
- `ai_model_management.view` — Screen loaded
- `ai_model_management.deploy` — Model deployed
- `ai_model_management.deactivate` — Model deactivated
- `ai_model_management.config_change` — Config updated

## Implementation Notes
- Model cards with status and metrics
- Performance charts for monitoring
- Configuration form for settings
- AiDock provides model insights
- Version management for models
