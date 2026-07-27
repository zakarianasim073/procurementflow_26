# KpiCard Component Contract

**Package**: `shared/ui`  
**Type**: Display Component  
**Stability**: Stable  

---

## Purpose

Displays a single Key Performance Indicator with value, label, trend, and optional sparkline. Used in dashboard KPI strips, executive summaries, and report headers.

---

## Props

```typescript
interface KpiCardProps {
  /** KPI label */
  label: string;
  /** Primary value (number, string, or formatted) */
  value: string | number;
  /** Unit/suffix (e.g., "BDT", "%", "M") */
  unit?: string;
  /** Trend indicator */
  trend?: {
    value: number;        // percentage change
    label: string;        // "vs last month"
    isPositive?: boolean; // default: true
    period?: string;      // "30d", "90d", "YoY"
  };
  /** Sparkline data points */
  sparkline?: number[];
  /** Value formatter */
  format?: 'number' | 'currency' | 'percentage' | 'compact' | 'custom';
  /** Custom formatter function */
  formatter?: (value: number) => string;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string;
  /** Icon (Lucide icon name or component) */
  icon?: React.ReactNode;
  /** Color theme */
  color?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Click handler */
  onClick?: () => void;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `prefix` | No | Content before value (e.g., currency symbol) |
| `suffix` | No | Content after value (e.g., "/month") |
| `action` | No | Drill-down link or button |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Card with value, label, trend |
| `loading` | `loading=true` | Skeleton: label + value shimmer |
| `error` | `error` prop | Red border, error icon, message |
| `hover` | Mouse enter | Subtle elevation, cursor pointer if `onClick` |
| `focus` | Keyboard | Ring outline |

---

## Accessibility

- **Role**: `region` with `aria-label="${label}: ${formattedValue}"`
- **Live Region**: `aria-live="polite"` for value changes
- **Keyboard**: Focusable if `onClick` provided
- **Color**: Trend colors meet WCAG AA (not color-only)
- **Screen Reader**: Announces "KPI [label], value [value], trend [direction] [percentage]"

---

## Loading

- **Skeleton**: `KpiCardSkeleton` — 3 lines (label, value, trend)
- **Delay**: 100ms before showing skeleton

---

## Errors

- **Display**: Inline error message below value
- **Icon**: `AlertTriangle` in `text-danger`
- **Retry**: Optional retry button in `action` slot

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate to card |
| `Enter` / `Space` | Trigger `onClick` |

---

## Mobile

- **< 640px**: Full-width in KpiStrip (horizontal scroll)
- **Min Width**: 160px per card
- **Touch**: No special gestures

---

## Permissions

| Role | View |
|------|------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `kpi_card_view` | `label`, `has_trend`, `has_sparkline`, `size` |
| `kpi_card_click` | `label`, `action` |

---

## React Query

```typescript
// KPIs typically fetched via dashboard/stats or executive/overview
const { data } = useQuery({
  queryKey: dashboardKeys.stats(),
  select: (data) => ({
    totalTenders: data.stats.total_tenders,
    winRate: data.stats.win_rate,
    // ...
  })
});
```

---

## Dependencies

- `Sparkline` (optional, for trend visualization)
- `TrendBadge` (for trend display)
- `CurrencyDisplay` / `PercentageDisplay` (formatters)
- `lucide-react`: `TrendingUp`, `TrendingDown`, `Minus`, `AlertTriangle`

---

## Format Specifications

| Format | Example Input | Output |
|--------|---------------|--------|
| `number` | `1234567` | `1,234,567` |
| `currency` | `45000000` | `৳45,000,000` |
| `percentage` | `0.71` | `71%` |
| `compact` | `1234567` | `1.2M` |
| `custom` | `formatter(1234)` | `formatter` result |

---

## Future Extensions

- [ ] Animated value transitions
- [ ] Threshold-based color coding
- [ ] Comparison mode (actual vs target)
- [ ] Drill-down modal on click