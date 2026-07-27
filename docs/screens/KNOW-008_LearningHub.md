# KNOW-008: Learning Hub Screen Specification

**Module:** `features/learning/LearningHubPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
AI model training, performance monitoring, and continuous learning management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Learning Hub              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ LearningHubHeader (model status, metrics)        │
│          ├──────────────────────────────────────────────────┤
│          │ LearningHub (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Training] [Models] [Performance]    │   │
│          │ │ [Datasets]                                  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ TrainingDashboard (training status)         │   │
│          │ │ ModelList (trained models)                  │   │
│          │ │ PerformanceMetrics (charts)                 │   │
│          │ │ DatasetManager (training data)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (learning insights, optimization suggestions)        │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
LearningHubPage
├── ExecutiveHeader
├── Breadcrumb
├── LearningHubHeader
│   ├── KpiStrip (models, accuracy, last_training)
│   └── Button (Start Training)
├── LearningHub
│   ├── Tabs
│   │   ├── TrainingTab
│   │   │   └── TrainingDashboard
│   │   │       ├── TrainingJob × N
│   │   │       │   ├── model_name
│   │   │       │   ├── status
│   │   │       │   ├── progress
│   │   │       │   └── metrics
│   │   │       └── Button (New Training)
│   │   ├── ModelsTab
│   │   │   └── ModelList
│   │   │       └── ModelCard × N
│   │   │           ├── name
│   │   │           ├── version
│   │   │           ├── accuracy
│   │   │           ├── status
│   │   │           └── Button (Deploy)
│   │   ├── PerformanceTab
│   │   │   └── PerformanceMetrics
│   │   │       ├── Chart (accuracy_trend)
│   │   │       ├── Chart (loss_trend)
│   │   │       └── Table (per_class_metrics)
│   │   └── DatasetsTab
│   │       └── DatasetManager
│   │           ├── DatasetCard × N
│   │           │   ├── name
│   │           │   ├── size
│   │           │   ├── records
│   │           │   └── Button (Use)
│   │           └── Button (Upload Dataset)
│   └── TrainingConfig
│       ├── Select (model_type)
│       ├── Input (epochs)
│       ├── Input (learning_rate)
│       └── Button (Start Training)
└── AiDock
    ├── AgentCard (Learning Agent)
    └── EvidencePanel (learning insights)
```

## Data Sources

### Training Jobs
```typescript
// API: GET /api/v1/knowledge/training/jobs
interface TrainingJobList {
  jobs: TrainingJob[];
}

interface TrainingJob {
  job_id: string;
  model_name: string;
  status: 'queued' | 'training' | 'completed' | 'failed';
  progress: number;
  started_at: string;
  completed_at?: string;
  metrics?: TrainingMetrics;
}

interface TrainingMetrics {
  accuracy: number;
  loss: number;
  f1_score: number;
  precision: number;
  recall: number;
}
```

### Trained Models
```typescript
// API: GET /api/v1/knowledge/training/models
interface ModelList {
  models: Model[];
}

interface Model {
  model_id: string;
  name: string;
  version: string;
  accuracy: number;
  status: 'active' | 'inactive' | 'training';
  trained_at: string;
  dataset_id: string;
  metrics: TrainingMetrics;
}
```

### React Query
```typescript
const { data: jobs } = useQuery({
  queryKey: ['knowledge', 'training', 'jobs'],
  queryFn: () => api.get('/api/v1/knowledge/training/jobs'),
  refetchInterval: 10_000, // 10 seconds
});

const { data: models } = useQuery({
  queryKey: ['knowledge', 'training', 'models'],
  queryFn: () => api.get('/api/v1/knowledge/training/models'),
});

const startTraining = useMutation({
  mutationFn: (request: TrainingRequest) => api.post('/api/v1/knowledge/training/start', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'training'] });
    toast.success('Training started');
  },
});

const deployModel = useMutation({
  mutationFn: (modelId: string) => api.post(`/api/v1/knowledge/training/models/${modelId}/deploy`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'training'] });
    toast.success('Model deployed');
  },
});
```

## Zustand Store
```typescript
// stores/learningHubStore.ts
interface LearningHubState {
  activeTab: string;
  selectedModel: string | null;
  setTab: (tab: string) => void;
  setModel: (id: string | null) => void;
}
```

## Interactions

### Start Training
1. Click "Start Training"
2. Configure parameters
3. Select dataset
4. Start training
5. Monitor progress

### Deploy Model
1. Click Deploy button
2. Confirm deployment
3. Update model status
4. Activate model

### View Performance
1. Click Performance tab
2. View charts
3. Analyze metrics
4. Compare models

### Manage Datasets
1. Click Datasets tab
2. View dataset list
3. Upload new dataset
4. Select for training

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Jobs: Skeleton cards
- Models: Skeleton cards
- Performance: Skeleton charts

## Error States
- Training failure: Error details
- Deploy failure: Toast error
- Network error: Retry button

## Accessibility
- Cards are focusable
- Progress announced via `aria-live`
- Screen reader: "Training X% complete"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `learning_hub.view` — Screen loaded
- `learning_hub.train` — Training started
- `learning_hub.deploy` — Model deployed
- `learning_hub.dataset_upload` — Dataset uploaded

## Implementation Notes
- Real-time training progress
- Model version management
- Performance monitoring with charts
- AiDock provides learning insights
- Dataset management for training
