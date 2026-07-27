# KNOW-005: Training Data Screen Specification

**Module:** `features/knowledge/TrainingDataPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
AI model training data management, dataset creation, and model performance monitoring.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Training Data             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TrainingDataHeader (dataset count, last training)│
│          ├──────────────────────────────────────────────────┤
│          │ TrainingData (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Datasets] [Models] [Performance]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DatasetList (cards with stats)              │   │
│          │ │ ModelList (training history)                │   │
│          │ │ PerformanceMetrics (charts)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (training suggestions, data quality)                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TrainingDataPage
├── ExecutiveHeader
├── Breadcrumb
├── TrainingDataHeader
│   ├── KpiStrip (datasets, models, last_training)
│   └── Button (Create Dataset)
├── TrainingData
│   ├── Tabs
│   │   ├── DatasetsTab
│   │   │   └── DatasetList
│   │   │       └── DatasetCard × N
│   │   │           ├── name
│   │   │           ├── size
│   │   │           ├── records
│   │   │           ├── created_at
│   │   │           └── Button (Train)
│   │   ├── ModelsTab
│   │   │   └── ModelList
│   │   │       └── ModelCard × N
│   │   │           ├── name
│   │   │           ├── version
│   │   │           ├── accuracy
│   │   │           └── trained_at
│   │   └── PerformanceTab
│   │       └── PerformanceMetrics
│   │           ├── Chart (accuracy over time)
│   │           ├── Chart (loss over time)
│   │           └── Table (per-class metrics)
│   └── DatasetEditor
│       ├── Input (name)
│       ├── Textarea (description)
│       ├── FileUpload (data files)
│       └── Button (Save)
└── AiDock
    ├── AgentCard (Learning Agent)
    └── EvidencePanel (training insights)
```

## Data Sources

### Datasets
```typescript
// API: GET /api/v1/knowledge/training/datasets
interface DatasetList {
  datasets: Dataset[];
  total_count: number;
}

interface Dataset {
  dataset_id: string;
  name: string;
  description: string;
  size: number;
  record_count: number;
  file_count: number;
  created_at: string;
  updated_at: string;
  status: 'ready' | 'training' | 'error';
}
```

### Models
```typescript
// API: GET /api/v1/knowledge/training/models
interface ModelList {
  models: Model[];
}

interface Model {
  model_id: string;
  name: string;
  version: string;
  dataset_id: string;
  accuracy: number;
  loss: number;
  trained_at: string;
  status: 'active' | 'inactive' | 'training';
  metrics: ModelMetrics;
}

interface ModelMetrics {
  precision: number;
  recall: number;
  f1_score: number;
  confusion_matrix?: number[][];
}
```

### React Query
```typescript
const { data: datasets } = useQuery({
  queryKey: ['knowledge', 'training', 'datasets'],
  queryFn: () => api.get('/api/v1/knowledge/training/datasets'),
});

const { data: models } = useQuery({
  queryKey: ['knowledge', 'training', 'models'],
  queryFn: () => api.get('/api/v1/knowledge/training/models'),
});

const trainModel = useMutation({
  mutationFn: (request: TrainRequest) => api.post('/api/v1/knowledge/training/train', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'training'] });
    toast.success('Training started');
  },
});
```

## Zustand Store
```typescript
// stores/trainingDataStore.ts
interface TrainingDataState {
  activeTab: string;
  selectedDataset: string | null;
  setTab: (tab: string) => void;
  setDataset: (id: string | null) => void;
}
```

## Interactions

### Dataset Management
1. View dataset list
2. Click dataset card
3. View details
4. Edit or delete

### Model Training
1. Select dataset
2. Click Train button
3. Configure parameters
4. Start training
5. Monitor progress

### Performance Analysis
1. Click Performance tab
2. View charts
3. Compare models
4. Export metrics

### Model Deployment
1. Select model
2. Click Deploy button
3. Confirm deployment
4. Activate model

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Grid cards + charts |
| Tablet (768-1024px) | Stacked cards |
| Mobile (<768px) | List view, bottom tabs |

## Loading States
- Datasets: Skeleton cards
- Models: Skeleton cards
- Performance: Skeleton charts

## Error States
- Training failure: Error details
- Dataset error: Validation message
- Network error: Retry button

## Accessibility
- Cards are focusable
- Training status announced via `aria-live`
- Screen reader: "Dataset X, Y records"
- Keyboard: Enter to select, Delete to remove

## Telemetry
- `training_data.view` — Screen loaded
- `training_data.train` — Training started
- `training_data.deploy` — Model deployed
- `training_data.delete` — Dataset deleted

## Implementation Notes
- Dataset management with CRUD
- Model training with progress
- Performance monitoring with charts
- AiDock provides training insights
- Export for model sharing
