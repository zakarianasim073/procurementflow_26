# KpiStrip Component Contract

**Package**: `shared/ui`  
**Type**: Layout Component  
**Stability**: Stable  

---

## Purpose

Horizontal strip of KPI cards for dashboard headers and executive screens. Provides consistent metric display with responsive scrolling.

---

## Props

```typescript
interface KpiStripProps {
  /** KPI cards to display */
  items: KpiCardItem[];
  /** Scroll behavior */
  scroll?: 'auto' | 'scroll' | 'hidden';
  /** Gap between cards */
  gap?: 'sm' | 'md' | 'lg';
  /** Minimum card width */
  minCardWidth?: number;
  /** Show scroll indicators */
  showScrollIndicators?: boolean;
  /** Custom className */
  className?: string;
}

interface KpiCardItem {
  id: string;
  label: string;
  value: string | number;
  unit?: string;
  trend?: { value: number; label: string; isPositive?: boolean };
  icon?: React.ReactNode;
  color?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
  onClick?: () => void;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `children` | No | Custom render (overrides items) |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Horizontal strip with cards |
| `scrolling` | Touch/drag | Momentum scroll |
| `loading` | Data fetching | Skeleton cards |
| `empty` | No items | "No KPIs configured" |

---

## Accessibility

- **Role**: `region` with `aria-label="Key Performance Indicators"`
- **Cards**: `article` with `aria-label="[label]: [value]"`
- **Scroll**: `aria-orientation="horizontal"`
- **Keyboard**: Tab to first card, arrow keys scroll

---

## Loading

- **Skeleton**: 4 card skeletons with shimmer
- **Delay**: 100ms

---

## Errors

- Not applicable (container only)

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus first card |
| `←/→` | Scroll horizontally |
| `Home/End` | First/last card |
| `Enter` | Trigger card click |

---

## Mobile

- **< 640px**: Horizontal scroll with snap points
- **Touch**: Native momentum scrolling
- **Indicators**: Fade-in/out scroll shadows
- **Card Width**: Min 160px, max 200px

---

## Permissions

| Role | View |
|------|------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `kpi_strip_view` | `item_count`, `scroll_used` |
| `kpi_card_click` | `kpi_id`, `label` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: dashboardKeys.stats(),
  select: (data) => [
    { id: 'tenders', label: 'Total Tenders', value: data.stats.total_tenders },
    { id: 'comparisons', label: 'Comparisons', value: data.stats.total_comparisons },
    // ...
  ]
});
```

---

## Dependencies

- `KpiCard` (individual card component)
- `ScrollShadows` (fade indicators)
- `lucide-react`: `TrendingUp`, `TrendingDown`, `Minus`

---

## Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ [KPI 1]  [KPI 2]  [KPI 3]  [KPI 4]  [KPI 5]  ▶                │
│  1,247     389       15,234     71%      48.7M                 │
│  Tenders  Compar.   BOQ Items  Win Rate  Pipeline              │
│  ↑12%     ↑3%       ↑8%        ↑2%        ↑8%                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Future Extensions

- [ ] Real-time value updates
- [ ] Drill-down modal on click
- [ ] Customizable card order
- [ ] Period selector (MTD/QTD/YTD)
- [ ] Export strip as image