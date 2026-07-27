# Calendar Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Full-featured calendar for date selection, scheduling, and event display. Supports single date, range, multiple dates, and recurring events.

---

## Props

```typescript
interface CalendarProps {
  /** Selected date(s) */
  value: Date | Date[] | DateRange | null;
  /** Change handler */
  onChange: (date: Date | Date[] | DateRange | null) => void;
  /** Selection mode */
  mode?: 'single' | 'range' | 'multiple';
  /** Min selectable date */
  minDate?: Date;
  /** Max selectable date */
  maxDate?: Date;
  /** Disabled dates */
  disabledDates?: Date[] | ((date: Date) => boolean);
  /** Disabled days of week (0=Sun) */
  disabledDaysOfWeek?: number[];
  /** First day of week (0=Sun, 1=Mon) */
  weekStartsOn?: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  /** Locale */
  locale?: string; // default: 'en-US'
  /** Events to display */
  events?: CalendarEvent[];
  /** Event click handler */
  onEventClick?: (event: CalendarEvent) => void;
  /** Date click handler */
  onDateClick?: (date: Date, events: CalendarEvent[]) => void;
  /** Show week numbers */
  showWeekNumbers?: boolean;
  /** Show today highlight */
  showToday?: boolean;
  /** Show outside days */
  showOutsideDays?: boolean;
  /** Inline (always open) */
  inline?: boolean;
  /** Custom day renderer */
  renderDay?: (date: Date, events: CalendarEvent[]) => React.ReactNode;
  /** Custom className */
  className?: string;
}

interface DateRange {
  start: Date;
  end: Date;
}

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end?: Date;
  allDay?: boolean;
  color?: string;
  description?: string;
  metadata?: Record<string, any>;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `day` | No | Custom day cell |
| `event` | No | Custom event rendering |
| `header` | No | Custom header (month/year) |
| `today` | No | Custom today button |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Current month |
| `open` | Click input | Popover visible |
| `range-selecting` | Range mode | Start selected, preview end |
| `loading` | Async events | Skeleton |
| `empty` | No events | "No events" |

---

## Accessibility

- **Role**: `grid` for calendar, `button` for days
- **ARIA**: `aria-label` on navigation, `aria-selected` on days
- **Keyboard**: Full grid navigation
- **Screen Reader**: Announces month/year, selected date, events

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Keys` | Navigate days |
| `Page Up/Down` | Previous/Next month |
| `Home` / `End` | First/Last day of month |
| `Enter` / `Space` | Select date |
| `Escape` | Close popover |
| `Shift+Arrow` | Extend range |
| `Ctrl+Arrow` | Navigate months |

---

## Mobile

- **< 640px**: Full-screen modal
- **Swipe**: Left/right for month navigation
- **Touch**: Tap to select, long press for event details
- **Safe Area**: Respects bottom inset

---

## Permissions

Not applicable

---

## Usage Examples

```tsx
// Single date
<Calendar
  value={selectedDate}
  onChange={setSelectedDate}
  minDate={new Date()}
/>

// Date range
<Calendar
  mode="range"
  value={dateRange}
  onChange={setDateRange}
  minDate={new Date()}
/>

// With events
<Calendar
  value={selectedDate}
  onChange={setSelectedDate}
  events={calendarEvents}
  onEventClick={(event) => openEventDetail(event)}
  renderDay={(date, events) => (
    <DayCell date={date} events={events} />
  )}
/>

// Inline (always visible)
<Calendar
  inline
  mode="multiple"
  value={selectedDates}
  onChange={setSelectedDates}
  events={projectDeadlines}
  onDateClick={(date, events) => openDayDetail(date, events)}
/>

// With custom day rendering
<Calendar
  value={date}
  onChange={setDate}
  renderDay={(date, events) => {
    const isHoliday = isPublicHoliday(date);
    const hasEvent = events.length > 0;
    return (
      <DayCell
        date={date}
        isHoliday={isHoliday}
        hasEvent={hasEvent}
        eventCount={events.length}
      />
    );
  }}
/>

// With events
const calendarEvents: CalendarEvent[] = [
  {
    id: 'evt-1',
    title: 'Tender Deadline',
    start: new Date('2026-01-15'),
    end: new Date('2026-01-15'),
    allDay: true,
    color: '#EF4444',
    description: 'Bridge construction tender closes'
  },
  {
    id: 'evt-2',
    title: 'BOQ Review Meeting',
    start: new Date('2026-01-20T10:00:00'),
    end: new Date('2026-01-20T11:30:00'),
    color: '#3B82F6',
    description: 'Review BOQ with team'
  }
];

<Calendar
  events={calendarEvents}
  onEventClick={(event) => openEventModal(event)}
/>
```

---

## Event Colors

| Color | Use Case |
|-------|----------|
| `#EF4444` | Deadlines, critical |
| `#3B82F6` | Meetings, reviews |
| `#22C55E` | Completed, approvals |
| `#F59E0B` | Pending, warnings |
| `#8B5CF6` | Personal, reminders |
| `#EC4899` | HR, admin |

---

## Future Extensions

- [ ] Recurring events (RRULE)
- [ ] Drag-and-drop event creation
- [ ] Time slot selection
- [ ] Resource calendars (rooms, people)
- [ ] iCal export/import
- [ ] Timezone support
- [ ] Agenda view