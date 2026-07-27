# DatePicker Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Date selection with single date, date range, presets, and localization. Used for tender deadlines, report periods, and filter date ranges.

---

## Props

```typescript
interface DatePickerProps {
  /** Selected date(s) */
  value: Date | Date[] | null;
  /** Change handler */
  onChange: (date: Date | Date[] | null) => void;
  /** Selection mode */
  mode?: 'single' | 'range' | 'multiple';
  /** Min date */
  minDate?: Date;
  /** Max date */
  maxDate?: Date;
  /** Disabled dates */
  disabledDates?: Date[] | ((date: Date) => boolean);
  /** Disabled days of week (0=Sun) */
  disabledDaysOfWeek?: number[];
  /** Show week numbers */
  showWeekNumbers?: boolean;
  /** Show time picker */
  showTime?: boolean;
  /** Time step (minutes) */
  timeStep?: 15 | 30 | 60;
  /** Locale */
  locale?: string;
  /** First day of week (0=Sun, 1=Mon) */
  weekStartsOn?: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  /** Preset ranges */
  presets?: PresetRange[];
  /** Inline (always open) */
  inline?: boolean;
  /** Trigger element */
  trigger?: React.ReactNode;
  /** Popper placement */
  placement?: 'bottom' | 'top' | 'left' | 'right';
  /** Input props (for non-inline) */
  inputProps?: InputProps;
  /** ClassName */
  className?: string;
}

interface PresetRange {
  label: string;
  start: Date;
  end: Date;
  icon?: React.ReactNode;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `trigger` | No | Custom trigger button |
| `header` | No | Custom header (month/year nav) |
| `day` | No | Custom day cell |
| `footer` | No | Presets, today, clear |
| `rangePreview` | No | Selected range display |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | Default | Trigger only |
| `open` | Click trigger | Calendar popover |
| `selecting` | Range start selected | Highlighted range |
| `loading` | Async validation | Spinner |
| `disabled` | `disabled=true` | Muted trigger |

---

## Accessibility

- **Role**: `dialog` (popover) / `application` (inline)
- **Calendar**: `role="grid"` with `role="gridcell"` days
- **Navigation**: `aria-label` on nav buttons
- **Selected**: `aria-selected`, `aria-current="date"`
- **Range**: `aria-label` with start/end
- **Keyboard**: Full calendar navigation
- **Screen Reader**: Announces month/year, selection

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus trigger / first day |
| `Enter` / `Space` | Select date / open |
| `Arrow Keys` | Navigate days |
| `Page Up/Down` | Previous/Next month |
| `Home` / `End` | First/Last day of month |
| `Ctrl+Page Up/Down` | Previous/Next year |
| `Escape` | Close |
| `Enter` (on Today) | Select today |

---

## Loading

Not typically async; instant open/close

---

## Error State

- **Invalid Range**: End before start → red highlight
- **Out of Bounds**: Outside min/max → disabled
- **Required**: Red border on trigger

---

## Mobile

- **Inline**: Full-width calendar
- **Popover**: Full-screen bottom sheet
- **Touch**: Swipe months, tap days
- **Presets**: Bottom sheet modal

---

## Permissions

Not applicable (form input)

---

## Telemetry

| Event | Properties |
|-------|------------|
| `datepicker_open` | `mode`, `inline` |
| `datepicker_select` | `date`, `mode`, `preset` |
| `datepicker_preset` | `preset_label` |
| `datepicker_navigate` | `direction`, `view` |

---

## React Query

```typescript
// Value typically from form state
const { data: report } = useQuery({
  queryKey: ['report', dateRange],
  queryFn: () => fetchReport(dateRange)
});
```

---

## Dependencies

- `Popover` (popover)
- `Button` (nav, presets)
- `Input` (year/month input)
- `lucide-react`: `Calendar`, `ChevronLeft`, `ChevronRight`, `X`, `Clock`, `CalendarDays`, `CalendarRange`

---

## Usage Examples

```tsx
// Single date
<DatePicker
  value={deadline}
  onChange={setDeadline}
  minDate={new Date()}
  placeholder="Select deadline"
/>

// Range with presets
<DatePicker
  mode="range"
  value={dateRange}
  onChange={setDateRange}
  presets={[
    { label: 'Last 7 days', start: subDays(new Date(), 7), end: new Date() },
    { label: 'Last 30 days', start: subDays(new Date(), 30), end: new Date() },
    { label: 'This month', start: startOfMonth(new Date()), end: endOfMonth(new Date()) },
    { label: 'Last month', start: startOfMonth(subMonths(new Date(), 1)), end: endOfMonth(subMonths(new Date(), 1)) },
  ]}
/>

// Inline with time
<DatePicker
  inline
  showTime
  timeStep={30}
  value={meetingTime}
  onChange={setMeetingTime}
/>

// Range with inline preview
<DatePicker
  mode="range"
  value={reportPeriod}
  onChange={setReportPeriod}
  renderRangePreview={(start, end) => (
    <span className="text-sm text-muted">
      {format(start, 'MMM d')} – {format(end, 'MMM d, yyyy')}
    </span>
  )}
/>
```

---

## Future Extensions

- [ ] Fiscal year presets
- [ ] Business days only
- [ ] Recurring date patterns
- [ ] Timezone support
- [ ] Drag to select range
- [ ] Keyboard shortcuts for presets