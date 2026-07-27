# CalendarRange Component Contract

**Module:** `shared/ui/CalendarRange`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Date range picker for filtering tenders by submission deadline, awards by contract period, and analytics by custom timeframes.

## Props
```typescript
interface CalendarRangeProps {
  value?: DateRange;
  onChange?: (range: DateRange) => void;
  minDate?: Date;
  maxDate?: Date;
  presets?: DatePreset[];
  showTime?: boolean;
  format?: string;
  locale?: string;
  numberOfMonths?: 1 | 2;
  selectEnd?: boolean;
  disabled?: boolean;
  error?: string;
  label?: string;
  placeholder?: string;
  className?: string;
  testId?: string;
}

interface DateRange {
  start: Date | null;
  end: Date | null;
}

interface DatePreset {
  label: string;
  range: () => DateRange;
  icon?: ReactNode;
}
```

## Slots
- `header` — Month/year navigation
- `calendar` — Date grid
- `presets` — Quick select buttons
- `footer` — Action buttons (Apply, Cancel, Clear)

## State
```typescript
interface CalendarRangeState {
  visibleMonth: Date;
  hoverDate: Date | null;
  selecting: 'start' | 'end';
}
```

## Accessibility
- **ARIA:** `role="dialog"`, `aria-label`, date cells have `aria-selected`
- **Keyboard:** Arrow keys navigate dates, Enter selects, Escape closes
- **Focus:** Visible focus ring on dates

## Loading
- N/A — synchronous

## Errors
- Invalid range message
- Min/max date constraint messages

## Keyboard
| Key | Action |
|-----|--------|
| ArrowRight | Next day |
| ArrowLeft | Previous day |
| ArrowDown | Next week |
| ArrowUp | Previous week |
| Enter | Select date |
| Escape | Close calendar |
| PageDown | Next month |
| PageUp | Previous month |

## Mobile
- Full-screen modal on small screens
- Scrollable month view
- Touch-friendly date selection

## Permissions
- No restrictions

## Telemetry
- `calendar_range.open` — Picker opened
- `calendar_range.select` — Range selected (days, preset)
- `calendar_range.preset` — Preset used

## React Query
- None — pure UI

## Dependencies
- `date-fns` for date manipulation
- `shared/ui/Button` for actions
- `shared/ui/IconButton` for navigation

## Future Extensions
- Time zone support
- Recurring date ranges
- Multi-range selection
- i18n locale packs
