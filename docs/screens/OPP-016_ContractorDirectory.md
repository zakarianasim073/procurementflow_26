# OPP-016: Contractor Directory Screen Specification

**Module:** `features/contractor-directory/ContractorDirectoryPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Opportunity

## Purpose
Browse, search, and manage contractor profiles and directories.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Opportunity > Contractor Directory    │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ContractorDirectoryHeader (count, filters)       │
│          ├──────────────────────────────────────────────────┤
│          │ ContractorDirectory (main content)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (contractor search)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FilterPanel (specialization, rating)        │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ContractorGrid (contractor cards)           │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │Contr.│Contr.│Contr.│Contr.│              │   │
│          │ │ │  A   │  B   │  C   │  D   │              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ContractorDetails (selected contractor)     │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (contractor insights)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ContractorDirectoryPage
├── ExecutiveHeader
├── Breadcrumb
├── ContractorDirectoryHeader
│   ├── KpiStrip (contractor_count, avg_rating)
│   └── Button (Add Contractor)
├── ContractorDirectory
│   ├── SearchBar
│   │   └── SearchInput
│   ├── FilterPanel
│   │   ├── ChipSelect (specialization)
│   │   ├── ChipSelect (rating)
│   │   ├── ChipSelect (location)
│   │   └── ChipSelect (status)
│   ├── ContractorGrid
│   │   └── ContractorCard × N
│   │       ├── name
│   │       ├── specialization
│   │       ├── rating
│   │       ├── projects_count
│   │       ├── location
│   │       └── Button (View Profile)
│   ├── ContractorDetails
│   │   ├── profile_info
│   │   ├── project_history
│   │   ├── certifications
│   │   └── contact_info
│   └── ContractorStats
│       ├── chart (by_specialization)
│       ├── chart (by_rating)
│       └── chart (by_location)
└── AiDock
    ├── AgentCard (Contractor Agent)
    └── EvidencePanel (contractor insights)
```

## Data Sources

### Contractors
```typescript
// API: GET /api/v1/opportunities/contractors
interface ContractorDirectory {
  contractors: Contractor[];
  total_count: number;
  filters: FilterOptions;
}

interface Contractor {
  contractor_id: string;
  name: string;
  specialization: string[];
  rating: number;
  projects_count: number;
  location: string;
  status: 'active' | 'inactive' | 'suspended';
  certifications: string[];
  contact: ContactInfo;
}

interface ContactInfo {
  email: string;
  phone: string;
  address: string;
}

interface FilterOptions {
  specializations: string[];
  ratings: string[];
  locations: string[];
}
```

### React Query
```typescript
const { data: directory } = useQuery({
  queryKey: ['opportunities', 'contractors', filters],
  queryFn: () => api.get('/api/v1/opportunities/contractors', { params: filters }),
});

const { data: contractor } = useQuery({
  queryKey: ['opportunities', 'contractors', contractorId],
  queryFn: () => api.get(`/api/v1/opportunities/contractors/${contractorId}`),
  enabled: !!contractorId,
});
```

## Zustand Store
```typescript
// stores/contractorDirectoryStore.ts
interface ContractorDirectoryState {
  searchQuery: string;
  filters: {
    specialization: string[];
    rating: string[];
    location: string[];
    status: string[];
  };
  selectedContractor: string | null;
  setSearch: (query: string) => void;
  setFilter: <K extends keyof ContractorDirectoryState['filters']>(key: K, value: ContractorDirectoryState['filters'][K]) => void;
  setContractor: (id: string | null) => void;
}
```

## Interactions

### Search Contractors
1. Type query
2. Search contractors
3. View results
4. Select contractor

### Filter Directory
1. Apply filters
2. Update grid
3. Preserve view
4. Refresh display

### View Profile
1. Click contractor card
2. View details
3. Check history
4. Review certifications

### Contact Contractor
1. Click Contact
2. View contact info
3. Send message
4. Track communication

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + details |
| Tablet (768-1024px) | Grid with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Contractors: Skeleton cards
- Details: Loading spinner
- Stats: Loading charts

## Error States
- Load failure: Retry button
- Search failure: Toast error
- Network error: Toast notification

## Accessibility
- Contractors are focusable
- Count announced via `aria-live`
- Screen reader: "Contractor: ABC Corp, rating: 4.5"
- Keyboard: Tab through contractors

## Telemetry
- `contractor_directory.view` — Screen loaded
- `contractor_directory.search` — Search performed
- `contractor_directory.filter` — Filter applied
- `contractor_directory.view_profile` — Profile viewed

## Implementation Notes
- Contractor directory
- Advanced filtering
- Profile management
- AiDock provides contractor insights
- Export for analysis
