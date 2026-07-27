# TEN-025: Tender Calendar Screen Specification

**Module:** `features/tender-calendar/TenderCalendarPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Calendar view for tender deadlines, submissions, and important dates.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Tender Calendar         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderCalendarHeader (date, events)              │
│          ├──────────────────────────────────────────────────┤
│          │ TenderCalendar (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ CalendarView (monthly/weekly/daily)         │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │     July 2026                            ││   │
│          │ │ │ Su Mo Tu We Th Fr Sa                     ││   │
│          │ │ │        1  2  3  4                         ││   │
│          │ │ │  5  6  7  8  9 10 11                     ││   │
│          │ │ │ 12 13 14 15 16 17 18                     ││   │
│          │ │ │ 19 20 21 22 23 24 25                     ││   │
│          │ │ │ 26 27 28 29 30 31                        ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ EventList (events for selected date)        │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (calendar insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TenderCalendarPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderCalendarHeader
│   ├── KpiStrip (upcoming_count, overdue_count)
│   └── Button (Add Event)
├── TenderCalendar
│   ├── CalendarView
│   │   ├── CalendarHeader
│   │   │   ├── prev/next buttons
│   │   │   ├── month/year display
│   │   │   └── view toggle (month/week/day)
│   │   ├── CalendarGrid
│   │   │   └── DayCell × N
│   │   │       ├── date
│   │   │       ├── events_count
│   │   │       └── EventMarker × N
│   │   └── EventPopup
│   │       └── EventDetail
│   │           ├── tender_name
│   │           ├── deadline
│   │           └── Button (View Tender)
│   ├── EventList
│   │   └── EventCard × N
│   │       ├── tender_name
│   │       ├── event_type
│   │       ├── date
│   │       ├── status
│   │       └── Button (View Details)
│   └── CalendarStats
│       ├── chart (events_by_month)
│       ├── chart (by_type)
│       └── chart (upcoming_deadlines)
└── AiDock
    ├── AgentCard (Calendar Agent)
    └── EvidencePanel (calendar insights)
```

## Data Sources

### Calendar Events
```typescript
// API: GET /api/v1/tenders/calendar
interface CalendarData {
  events: CalendarEvent[];
  upcoming_count: number;
  overdue_count: number;
}

interface CalendarEvent {
  event_id: string;
  tender_id: string;
  tender_name: string;
  event_type: 'deadline' | 'submission' | 'opening' | 'award';
  date: string;
  status: 'upcoming' | 'completed' | 'overdue';
  description?: string;
}
```

### React Query
```typescript
const { data: calendar } = useQuery({
  queryKey: ['tenders', 'calendar', { month, year }],
  queryFn: () => api.get('/api/v1/tenders/calendar', { params: { month, year } }),
});

const addEvent = useMutation({
  mutationFn: (event: CreateEventRequest) => api.post('/api/v1/tenders/calendar', event),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'calendar'] });
    toast.success('Event added');
  },
});
```

## Zustand Store
```typescript
// stores/tenderCalendarStore.ts
interface TenderCalendarState {
  currentDate: Date;
  viewMode: 'month' | 'week' | 'day';
  selectedDate: Date | null;
  setCurrentDate: (date: Date) => void;
  setViewMode: (mode: string) => void;
  setSelectedDate: (date: Date | null) => void;
}
```

## Interactions

### Navigate Calendar
1. Click prev/next buttons
2. Change month/year
3. Update calendar
4. Preserve selection

### Select Date
1. Click day cell
2. View events
3. Show event list
4. Highlight selection

### Add Event
1. Click Add Event
2. Select date
3. Enter details
4. Save event

### View Event
1. Click event marker
2. View popup
3. Read details
4. Navigate to tender

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full calendar + list |
| Tablet (768-1024px) | Calendar with popup |
| Mobile (<768px) | List view |

## Loading States
- Calendar: Loading grid
- Events: Skeleton cards
- Stats: Loading charts

## Error States
- Load failure: Retry button
- Add failure: Toast error
- Network error: Toast notification

## Accessibility
- Days are focusable
- Events announced via `aria-live`
- Screen reader: "July 15, 2 events"
- Keyboard: Arrow keys to navigate

## Telemetry
- `tender_calendar.view` — Screen loaded
- `tender_calendar.navigate` — Calendar navigated
- `tender_calendar.event_add` — Event added
- `tender_calendar.event_view` — Event viewed

## Implementation Notes
- Interactive calendar
- Event management
- Deadline tracking
- AiDock provides calendar insights
- Export for planning
