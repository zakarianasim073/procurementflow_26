# ChipSelect Component Contract

**Module:** `shared/ui/ChipSelect`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Multi-select dropdown that renders selected values as dismissible chips, used for filter panels (agencies, tender status, zones, divisions) and tag assignment.

## Props
```typescript
interface ChipSelectProps<T> {
  options: ChipOption<T>[];
  value: T[];
  onChange: (value: T[]) => void;
  placeholder?: string;
  maxChips?: number;
  searchable?: boolean;
  disabled?: boolean;
  error?: string;
  label?: string;
  renderChip?: (option: ChipOption<T>, onRemove: () => void) => ReactNode;
  renderOption?: (option: ChipOption<T>, selected: boolean) => ReactNode;
  groupBy?: (option: ChipOption<T>) => string;
  className?: string;
  testId?: string;
}

interface ChipOption<T> {
  value: T;
  label: string;
  icon?: ReactNode;
  disabled?: boolean;
  description?: string;
}
```

## Slots
- `chip` — Custom chip renderer
- `option` — Custom dropdown option renderer
- `empty` — No results state
- `header` — Dropdown header (select all, clear all)

## State
```typescript
interface ChipSelectState {
  isOpen: boolean;
  searchQuery: string;
  highlightedIndex: number;
}
```

## Accessibility
- **ARIA:** `role="combobox"`, `aria-expanded`, `aria-autocomplete="list"`, chip has `role="option"` with remove button
- **Keyboard:** Backspace removes last chip, Arrow keys navigate options, Enter selects, Escape closes
- **Focus:** Input stays focused, chips are focusable for removal

## Loading
- Skeleton chips during initial load

## Errors
- Error message below component
- Invalid state border

## Keyboard
| Key | Action |
|-----|--------|
| Backspace | Remove last chip |
| ArrowDown | Next option |
| ArrowUp | Previous option |
| Enter | Toggle highlighted option |
| Escape | Close dropdown |
| Ctrl+A | Select all options |

## Mobile
- Full-screen modal with search
- Larger touch targets
- Scrollable option list

## Permissions
- Options filtered by user permissions

## Telemetry
- `chip_select.add` — Chip added (value)
- `chip_select.remove` — Chip removed (value)
- `chip_select.search` — Search performed

## React Query
- Options may come from API query
- Parent manages query state

## Dependencies
- `shared/ui/Badge` — Chip styling
- `shared/hooks/useClickOutside` — Dropdown dismiss
- `shared/hooks/useDebounce` — Search debounce

## Future Extensions
- Drag-to-reorder chips
- Category grouping with headers
- Recent selections
- Create-new option inline
