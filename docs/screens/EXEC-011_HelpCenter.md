# EXEC-011: Help Center Screen Specification

**Module:** `features/help-center/HelpCenterPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
In-app help, guided tours, and support resources.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Help Center               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ HelpCenterHeader (search, quick links)           │
│          ├──────────────────────────────────────────────────┤
│          │ HelpCenter (main content)                        │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (help search)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ QuickLinks (common tasks)                   │   │
│          │ │ ┌──────────────┐ ┌──────────────┐          │   │
│          │ │ │ Getting      │ │ Keyboard     │          │   │
│          │ │ │ Started      │ │ Shortcuts    │          │   │
│          │ │ └──────────────┘ └──────────────┘          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Guides] [Videos] [FAQ] [Contact]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ GuideList (documentation)                   │   │
│          │ │ VideoList (tutorials)                       │   │
│          │ │ FaqList (questions)                         │   │
│          │ │ ContactForm (support)                       │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (help suggestions, guided tours)                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
HelpCenterPage
├── ExecutiveHeader
├── Breadcrumb
├── HelpCenterHeader
│   ├── SearchBar (help search)
│   └── QuickLinks
│       ├── Button (Getting Started)
│       ├── Button (Keyboard Shortcuts)
│       └── Button (Contact Support)
├── HelpCenter
│   ├── SearchBar (prominent)
│   ├── QuickLinks
│   │   └── QuickLink × N
│   │       ├── icon
│   │       ├── title
│   │       └── Button (Start)
│   ├── Tabs
│   │   ├── GuidesTab
│   │   │   └── GuideList
│   │   │       └── GuideCard × N
│   │   │           ├── icon
│   │   │           ├── title
│   │   │           ├── description
│   │   │           └── Button (Read)
│   │   ├── VideosTab
│   │   │   └── VideoList
│   │   │       └── VideoCard × N
│   │   │           ├── thumbnail
│   │   │           ├── title
│   │   │           ├── duration
│   │   │           └── Button (Watch)
│   │   ├── FaqTab
│   │   │   └── FaqList
│   │   │       └── FaqItem × N
│   │   │           ├── question
│   │   │           ├── answer (expandable)
│   │   │           └── category
│   │   └── ContactTab
│   │       └── ContactForm
│   │           ├── Input (name)
│   │           ├── Input (email)
│   │           ├── Select (category)
│   │           ├── Textarea (message)
│   │           └── Button (Submit)
│   └── GuidedTour
│       └── TourStep × N
│           ├── title
│           ├── description
│           └── Button (Next)
└── AiDock
    ├── AgentCard (Help Agent)
    └── EvidencePanel (help suggestions)
```

## Data Sources

### Help Content
```typescript
// API: GET /api/v1/help
interface HelpContent {
  guides: Guide[];
  videos: Video[];
  faqs: FaqItem[];
}

interface Guide {
  guide_id: string;
  title: string;
  description: string;
  icon: string;
  content: string;
  read_time: number;
}

interface Video {
  video_id: string;
  title: string;
  thumbnail_url: string;
  video_url: string;
  duration: number;
}

interface FaqItem {
  faq_id: string;
  question: string;
  answer: string;
  category: string;
  helpful_count: number;
}
```

### React Query
```typescript
const { data: help } = useQuery({
  queryKey: ['help'],
  queryFn: () => api.get('/api/v1/help'),
});

const submitTicket = useMutation({
  mutationFn: (request: SubmitTicketRequest) => api.post('/api/v1/help/tickets', request),
  onSuccess: () => {
    toast.success('Support ticket submitted');
  },
});
```

## Zustand Store
```typescript
// stores/helpCenterStore.ts
interface HelpCenterState {
  activeTab: string;
  searchQuery: string;
  setTab: (tab: string) => void;
  setSearch: (query: string) => void;
}
```

## Interactions

### Search Help
1. Type in search bar
2. Debounce 300ms
3. Filter results
4. Show matching content

### View Guide
1. Click guide card
2. Open guide content
3. Read documentation
4. Mark as read

### Watch Video
1. Click video card
2. Open video player
3. Watch tutorial
4. Track progress

### Submit Ticket
1. Click Contact tab
2. Fill form
3. Submit ticket
4. Show confirmation

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with content |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Guides: Skeleton cards
- Videos: Skeleton thumbnails
- FAQ: Skeleton items

## Error States
- Search failure: Retry button
- Submit failure: Toast error
- Network error: Toast notification

## Accessibility
- Search results announced via `aria-live`
- FAQ items are expandable
- Screen reader: "Guide: Getting Started"
- Keyboard: Enter to open, Escape to close

## Telemetry
- `help_center.view` — Screen loaded
- `help_center.search` — Search performed
- `help_center.guide_view` — Guide viewed
- `help_center.video_watch` — Video watched
- `help_center.ticket_submit` — Ticket submitted

## Implementation Notes
- Prominent search bar
- Quick links for common tasks
- Guided tours for onboarding
- AiDock provides help suggestions
- Export for offline access
