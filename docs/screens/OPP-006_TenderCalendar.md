# OPP-006: Tender Calendar Screen Specification

**Module:** `features/tender-calendar/TenderCalendarPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
Tender deadline calendar, submission scheduling, and time-based tender management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Discovery > Tender Calendar           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderCalendarHeader (view toggle, filters)      │
│          ├──────────────────────────────────────────────────┤
│          │ TenderCalendar (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ViewToggle (month/week/day)                 │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ CalendarView (calendar grid)                │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Mon  Tue  Wed  Thu  Fri  Sat  Sun       ││   │
│          │ │ │  1    2    3    4    5    6    7        ││   │
│          │ │ │  [T1] [T2] [T3] [T4] [T5] [T6] [T7]   ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ UpcomingDeadlines (list)                    │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (deadline insights, scheduling suggestions)          │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TenderCalendarPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderCalendarHeader
│   ├── ViewToggle (month/week/day)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Add Reminder)
├── TenderCalendar
│   ├── CalendarView
│   │   └── CalendarGrid
│   │       └── CalendarDay × N
│   │           ├── date
│   │           └── TenderCard × N
│   │               ├── title
│   │               ├── agency
│   │               └── deadline
│   ├── UpcomingDeadlines
│   │   └── DeadlineCard × N
│   │       ├── TenderCard (compact)
│   │       ├── days_until
│   │       └── Button (View)
│   └── EventDetail
│       ├── tender details
│       ├── deadline info
│       └── actions (view, analyze, qualify)
└── AiDock
    ├── AgentCard (Discovery Agent)
    └── EvidencePanel (deadline insights)
```

## Data Sources

### Calendar Data
```typescript
// API: GET /api/v1/tenders/calendar
interface CalendarData {
  tenders: CalendarTender[];
  reminders: Reminder[];
}

interface CalendarTender {
  tender_id: string;
  title: string;
  agency: string;
  zone: string;
  submission_deadline: string;
  estimated_value: number;
  status: string;
  win_probability?: number;
}

interface Reminder {
  reminder_id: string;
  tender_id: string;
  title: string;
  remind_at: string;
  sent: boolean;
}
```

### React Query
```typescript
const { data: calendar } = useQuery({
  queryKey: ['tenders', 'calendar', month, year],
  queryFn: () => api.get('/api/v1/tenders/calendar', { params: { month, year } }),
});

const addReminder = useMutation({
  mutationFn: (request: AddReminderRequest) => api.post('/api/v1/tenders/reminders', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'calendar'] });
    toast.success('Reminder added');
  },
});
```

## Zustand Store
```typescript
// stores/tenderCalendarStore.ts
interface TenderCalendarState {
  viewMode: 'month' | 'week' | 'day';
  selectedDate: string | null;
  selectedTender: string | null;
  setViewMode: (mode: string) => void;
  setDate: (date: string | null) => void;
  setTender: (id: string | null) => void;
}
```

## Interactions

### Navigate Calendar
1. Click prev/next buttons
2. Update month/year
3. Refetch calendar data
4. Update view

### Select Date
1. Click calendar day
2. Highlight date
3. Show tenders for date
4. Update detail panel

### View Tender
1. Click tender card
2. Open TenderDetail drawer
3. View full details
4. Take action

### Add Reminder
1. Click "Add Reminder"
2. Select tender
3. Set reminder time
4. Save reminder

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full calendar + sidebar |
| Tablet (768-1024px) | Stacked calendar |
| Mobile (<768px) | Day view, swipe navigation |

## Loading States
- Calendar: Skeleton grid
- Tenders: Skeleton cards
- Detail: Skeleton content

## Error States
- Load failure: Retry button
- Add reminder failure: Toast error
- Network error: Toast notification

## Accessibility
- Calendar cells are focusable
- Deadlines announced via `aria-live`
- Screen reader: "3 tenders due on Jan 15"
- Keyboard: Arrow keys to navigate, Enter to select

## Telemetry
- `tender_calendar.view` — Screen loaded
- `tender_calendar.date_select` — Date selected
- `tender_calendar.tender_view` — Tender viewed
- `tender_calendar.reminder_add` — Reminder added

## Implementation Notes
- Month/week/day views
- Upcoming deadlines sidebar
- Reminder system
- AiDock provides deadline insights
- Export for scheduling
