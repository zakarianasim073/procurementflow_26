# TenderCard Component Contract

**Package**: `shared/ui`  
**Type**: Display Component  
**Stability**: Stable  

---

## Purpose

Displays a tender summary in a compact card format. Used in tender lists, dashboard widgets, and search results. Shows key tender metadata with visual status indicators.

---

## Props

```typescript
interface TenderCardProps {
  /** Tender data object */
  tender: {
    id: string;
    tenderNo: string;
    packageNo: string;
    title: string;
    agency: 'BWDB' | 'PWD' | 'LGED' | 'BPDB';
    zone: 'A' | 'B' | 'C' | 'D';
    estimatedValue: number;
    closingDate: string; // ISO 8601
    status: 'ACTIVE' | 'CLOSED' | 'AWARDED' | 'CANCELLED';
    winProbability?: number; // 0-1
  };
  /** Display variant */
  variant?: 'default' | 'compact' | 'detailed';
  /** Show win probability badge */
  showWinProbability?: boolean;
  /** Click handler */
  onClick?: (tenderId: string) => void;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom header content (agency badge, status) |
| `actions` | No | Action buttons (view, compare, track) |
| `footer` | No | Additional metadata (days left, documents count) |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial render | Card with border, hover elevation |
| `hover` | Mouse enter | `shadow-md`, `translate-y-[-2px]` |
| `loading` | Data fetching | Skeleton with shimmer |
| `selected` | Keyboard focus | `ring-2 ring-brand-500` |
| `disabled` | `onClick` not provided | `opacity-50 cursor-not-allowed` |

---

## Accessibility

- **Role**: `article` (or `button` if `onClick` provided)
- **ARIA**: `aria-label` with tender title + status
- **Keyboard**: Enter/Space activates if clickable
- **Focus**: Visible ring on focus-visible
- **Screen Reader**: Status announced as "Tender [title], [status], closes [date]"

---

## Loading

- **Skeleton**: `KpiStripSkeleton` × 3 lines + status badge skeleton
- **Delay**: Show skeleton after 150ms to prevent flash

---

## Errors

- **Missing Data**: Show placeholder "—" for missing fields
- **Invalid Date**: Show "Invalid date" with warning icon
- **Image Error**: Not applicable (no images)

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Move to/from card |
| `Enter` / `Space` | Trigger `onClick` (if provided) |
| `Escape` | Clear focus |

---

## Mobile

- **< 640px**: Full-width, stacked layout
- **Touch**: 44×44mm tap target minimum
- **Swipe**: No swipe gestures

---

## Permissions

| User Role | Can View | Can Interact |
|-----------|-----------|--------------|
| `viewer` | ✅ | Read-only |
| `estimator` | ✅ | Click → BOQ |
| `compliance` | ✅ | Click → Compliance |
| `admin` | ✅ | Full access |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `tender_card_view` | `tender_id`, `variant`, `has_win_probability` |
| `tender_card_click` | `tender_id`, `action` |

---

## React Query

```typescript
// Used in list queries
const { data } = useQuery({
  queryKey: tenderKeys.list({ page, limit, filters }),
  select: (data) => data.tenders.map(t => ({
    ...t,
    winProbability: t.win_probability // normalized
  }))
});
```

---

## Dependencies

- `KpiCard` (for win probability badge)
- `StatusBadge` (for tender status)
- `DateDisplay` (for closing date)
- `CurrencyDisplay` (for estimated value)
- `lucide-react` icons: `FileText`, `Calendar`, `MapPin`, `TrendingUp`

---

## Future Extensions

- [ ] Drag-to-reorder in tender lists
- [ ] Inline document count with popover
- [ ] Real-time status updates via WebSocket
- [ ] Comparison checkbox for multi-select