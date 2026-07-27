# EXEC-005: Help & Support Screen Specification

**Module:** `features/help/HelpSupportPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Help documentation, support ticket management, and system guides.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Help & Support             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ HelpSupportHeader (search, quick links)          │
│          ├──────────────────────────────────────────────────┤
│          │ HelpSupport (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (help search)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Guides] [FAQ] [Tickets] [Contact]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ GuideList (documentation cards)             │   │
│          │ │ FaqList (expandable questions)              │   │
│          │ │ TicketList (support tickets)                │   │
│          │ │ ContactForm (support request)               │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (help suggestions, guided tours)                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
HelpSupportPage
├── ExecutiveHeader
├── Breadcrumb
├── HelpSupportHeader
│   ├── SearchBar (help search)
│   └── QuickLinks
│       ├── Button (Getting Started)
│       ├── Button (API Docs)
│       └── Button (Keyboard Shortcuts)
├── HelpSupport
│   ├── Tabs
│   │   ├── GuidesTab
│   │   │   └── GuideList
│   │   │       └── GuideCard × N
│   │   │           ├── icon
│   │   │           ├── title
│   │   │           ├── description
│   │   │           └── Button (Read)
│   │   ├── FaqTab
│   │   │   └── FaqList
│   │   │       └── FaqItem × N
│   │   │           ├── question
│   │   │           ├── answer (expandable)
│   │   │           └── category
│   │   ├── TicketsTab
│   │   │   └── TicketList
│   │   │       └── Table<Ticket>
│   │   │           ├── subject
│   │   │           ├── status
│   │   │           ├── created_at
│   │   │           └── Button (View)
│   │   └── ContactTab
│   │       └── ContactForm
│   │           ├── Input (name)
│   │           ├── Input (email)
│   │           ├── Select (category)
│   │           ├── Textarea (message)
│   │           └── Button (Submit)
│   └── GuideViewer
│       ├── title
│       ├── content
│       └── TableOfContents
└── AiDock
    ├── AgentCard (Help Agent)
    └── EvidencePanel (help suggestions)
```

## Data Sources

### Help Guides
```typescript
// API: GET /api/v1/help/guides
interface GuideList {
  guides: Guide[];
  categories: string[];
}

interface Guide {
  guide_id: string;
  title: string;
  description: string;
  category: string;
  content: string;
  read_time: number;
  last_updated: string;
}
```

### FAQ
```typescript
// API: GET /api/v1/help/faq
interface FaqList {
  faqs: FaqItem[];
  categories: string[];
}

interface FaqItem {
  faq_id: string;
  question: string;
  answer: string;
  category: string;
  helpful_count: number;
}
```

### Support Tickets
```typescript
// API: GET /api/v1/help/tickets
interface TicketList {
  tickets: Ticket[];
  total_count: number;
}

interface Ticket {
  ticket_id: string;
  subject: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  created_at: string;
  updated_at: string;
  messages: TicketMessage[];
}

interface TicketMessage {
  message_id: string;
  sender: 'user' | 'support';
  content: string;
  created_at: string;
}
```

### React Query
```typescript
const { data: guides } = useQuery({
  queryKey: ['help', 'guides'],
  queryFn: () => api.get('/api/v1/help/guides'),
});

const { data: faqs } = useQuery({
  queryKey: ['help', 'faq'],
  queryFn: () => api.get('/api/v1/help/faq'),
});

const { data: tickets } = useQuery({
  queryKey: ['help', 'tickets'],
  queryFn: () => api.get('/api/v1/help/tickets'),
});

const createTicket = useMutation({
  mutationFn: (request: CreateTicketRequest) => api.post('/api/v1/help/tickets', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['help', 'tickets'] });
    toast.success('Ticket created');
  },
});
```

## Zustand Store
```typescript
// stores/helpSupportStore.ts
interface HelpSupportState {
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
4. Show matching guides/FAQs

### Read Guide
1. Click guide card
2. Open GuideViewer
3. Read content
4. Navigate via table of contents

### Create Ticket
1. Click Contact tab
2. Fill form
3. Submit ticket
4. View in ticket list

### View Ticket
1. Click ticket row
2. Open ticket detail
3. View messages
4. Reply if needed

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with content |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Guides: Skeleton cards
- FAQ: Skeleton items
- Tickets: Skeleton table

## Error States
- Search failure: Retry button
- Ticket creation failure: Toast error
- Network error: Retry button

## Accessibility
- Search results announced via `aria-live`
- FAQ items are expandable
- Screen reader: "Guide: Getting Started"
- Keyboard: Enter to open, Escape to close

## Telemetry
- `help_support.view` — Screen loaded
- `help_support.search` — Search performed
- `help_support.guide_view` — Guide viewed
- `help_support.ticket_create` — Ticket created

## Implementation Notes
- Search across all help content
- GuideViewer for documentation
- FAQ with expandable answers
- Ticket management for support
- AiDock provides help suggestions
