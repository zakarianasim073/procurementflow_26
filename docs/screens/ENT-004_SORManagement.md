# ENT-004: SOR Management Screen Specification

**Module:** `features/sor/SorManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Schedule of Rates management, zone configuration, rate updates, and agency-specific SOR administration.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > SOR Management             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SorManagementHeader (agency, zone, stats)        │
│          ├──────────────────────────────────────────────────┤
│          │ SorManagement (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Rates] [Zones] [Import] [History]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RatesTable (sortable, filterable)          │   │
│          │ │ ZoneConfiguration (zone mapping)           │   │
│          │ │ ImportTool (CSV/PDF upload)                │   │
│          │ │ ChangeHistory (audit trail)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (rate suggestions, zone optimization)                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SorManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── SorManagementHeader
│   ├── ChipSelect (agencies: BWDB, PWD, LGED)
│   ├── ChipSelect (zones: A, B, C, D)
│   ├── KpiStrip (total_rates, last_updated, zones_active)
│   └── Button (Export Rates)
├── SorManagement
│   ├── Tabs
│   │   ├── RatesTab
│   │   │   └── RateAnalysisTable
│   │   │       ├── code
│   │   │       ├── description
│   │   │       ├── unit
│   │   │       ├── zone_a
│   │   │       ├── zone_b
│   │   │       ├── zone_c
│   │   │       └── zone_d
│   │   ├── ZonesTab
│   │   │   └── ZoneConfiguration
│   │   │       ├── ZoneMapping
│   │   │       └── DivisionMapping
│   │   ├── ImportTab
│   │   │   └── ImportTool
│   │   │       ├── FileUpload
│   │   │       ├── PreviewTable
│   │   │       └── Button (Import)
│   │   └── HistoryTab
│   │       └── ChangeHistory
│   │           └── Table<ChangeEntry>
│   └── RateEditor
│       ├── Input (code)
│       ├── Input (description)
│       ├── Input (unit)
│       ├── Input (zone_a)
│       ├── Input (zone_b)
│       ├── Input (zone_c)
│       └── Input (zone_d)
└── AiDock
    ├── AgentCard (SOR Agent)
    └── EvidencePanel (rate insights)
```

## Data Sources

### SOR Rates
```typescript
// API: GET /api/v1/sor/rates
interface SorRateList {
  rates: SorRate[];
  total_count: number;
  agencies: string[];
  zones: string[];
}

interface SorRate {
  rate_id: string;
  agency: string;
  code: string;
  description: string;
  unit: string;
  zone_a: number;
  zone_b: number;
  zone_c: number;
  zone_d: number;
  last_updated: string;
  updated_by: string;
}
```

### Zone Configuration
```typescript
// API: GET /api/v1/sor/zones
interface ZoneConfig {
  zones: Zone[];
  division_mapping: DivisionMapping[];
}

interface Zone {
  zone_id: string;
  name: string;
  letter: string;
  divisions: string[];
  districts: string[];
}

interface DivisionMapping {
  division: string;
  lgd_zone: string;
  pwd_zone: string;
  bwdb_zone: string;
}
```

### React Query
```typescript
const { data: rates } = useQuery({
  queryKey: ['sor', 'rates', filters],
  queryFn: () => api.get('/api/v1/sor/rates', { params: filters }),
});

const { data: zones } = useQuery({
  queryKey: ['sor', 'zones'],
  queryFn: () => api.get('/api/v1/sor/zones'),
});

const importRates = useMutation({
  mutationFn: (formData: FormData) => api.post('/api/v1/sor/import', formData),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['sor', 'rates'] });
    toast.success('Rates imported successfully');
  },
});
```

## Zustand Store
```typescript
// stores/sorManagementStore.ts
interface SorManagementState {
  activeTab: 'rates' | 'zones' | 'import' | 'history';
  selectedAgency: string;
  selectedZone: string;
  searchQuery: string;
  setTab: (tab: string) => void;
  setAgency: (agency: string) => void;
  setZone: (zone: string) => void;
  setSearch: (query: string) => void;
}
```

## Interactions

### Rate Edit
1. Click rate row
2. Open RateEditor
3. Edit zone values
4. Save changes
5. Refresh table

### Import Rates
1. Click Import tab
2. Upload CSV/PDF
3. Preview data
4. Confirm import
5. Refresh rates

### Zone Configuration
1. Click Zones tab
2. View zone mapping
3. Edit division mapping
4. Save changes

### Export Rates
1. Click Export button
2. Choose format (CSV/Excel)
3. Filter by agency/zone
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full table with tabs |
| Tablet (768-1024px) | Collapsible tabs |
| Mobile (<768px) | Card view, bottom tabs |

## Loading States
- Table: Skeleton rows
- Zones: Skeleton mapping
- Import: Progress indicator

## Error States
- Import failure: Toast error
- Save failure: Draft recovery
- Network error: Retry button

## Accessibility
- Table rows are focusable
- Changes announced via `aria-live`
- Screen reader: "Rate X, zone A: 100"
- Keyboard: Enter to edit, Escape to cancel

## Telemetry
- `sor_management.view` — Screen loaded
- `sor_management.rate_edit` — Rate edited
- `sor_management.import` — Rates imported
- `sor_management.export` — Rates exported

## Implementation Notes
- RateAnalysisTable for rate display
- ZoneConfiguration for zone mapping
- ImportTool for bulk updates
- ChangeHistory for audit trail
- AiDock provides rate insights
