# Chart Component Contract

**Package**: `widgets/charts`  
**Type**: Data Visualization Component  
**Stability**: Stable  

---

## Purpose

Reusable chart components for dashboards, reports, and analytics. Built on Recharts with consistent theming, responsiveness, and accessibility.

---

## Props (Base)

```typescript
interface BaseChartProps {
  /** Chart data */
  data: ChartDataPoint[];
  /** Data key for X axis */
  xKey: string;
  /** Data keys for Y axis */
  yKeys: string | string[];
  /** Axis labels */
  xLabel?: string;
  yLabel?: string;
  /** Chart title */
  title?: string;
  /** Subtitle */
  subtitle?: string;
  /** Height */
  height?: number; // default: 300
  /** Width (responsive if not set) */
  width?: number;
  /** Colors */
  colors?: string[];
  /** Show legend */
  legend?: boolean; // default: true
  /** Show tooltip */
  tooltip?: boolean; // default: true
  /** Show grid */
  grid?: boolean; // default: true
  /** Animation */
  animation?: boolean; // default: true
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string;
  /** Custom className */
  className?: string;
}

interface ChartDataPoint {
  [key: string]: string | number | Date | null;
}
```

---

## Chart Types

| Type | Component | Use Case |
|------|-----------|----------|
| Line | `LineChart` | Trends over time |
| Area | `AreaChart` | Cumulative trends |
| Bar | `BarChart` | Categorical comparison |
| Horizontal Bar | `HorizontalBarChart` | Long labels |
| Stacked Bar | `StackedBarChart` | Part-to-whole |
| Pie | `PieChart` | Proportions |
| Donut | `DonutChart` | Proportions with center |
| Scatter | `ScatterChart` | Correlations |
| Radar | `RadarChart` | Multi-dimensional |
| Radial Bar | `RadialBarChart` | Progress/KPIs |
| Combo | `ComposedChart` | Mixed types |

---

## Props (Per Type)

### Line/Area Chart
```typescript
interface LineChartProps extends BaseChartProps {
  /** Curve type */
  curve?: 'linear' | 'monotone' | 'natural' | 'step' | 'basis';
  /** Show dots */
  dots?: boolean;
  /** Dot size */
  dotSize?: number;
  /** Connect nulls */
  connectNulls?: boolean;
  /** Reference lines */
  referenceLines?: ReferenceLine[];
}
```

### Bar Chart
```typescript
interface BarChartProps extends BaseChartProps {
  /** Bar layout */
  layout?: 'vertical' | 'horizontal';
  /** Bar gap */
  barGap?: number;
  /** Category gap */
  categoryGap?: number | string;
  /** Max bar width */
  maxBarWidth?: number;
  /** Rounded corners */
  radius?: number | [number, number, number, number];
}
```

### Pie/Donut Chart
```typescript
interface PieChartProps extends BaseChartProps {
  /** Inner radius (donut) */
  innerRadius?: number;
  /** Outer radius */
  outerRadius?: number;
  /** Start angle */
  startAngle?: number;
  /** End angle */
  endAngle?: number;
  /** Label line */
  labelLine?: boolean;
  /** Label position */
  labelPosition?: 'inside' | 'outside' | 'center';
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `legend` | No | Custom legend |
| `tooltip` | No | Custom tooltip |
| `label` | No | Custom data labels |
| `reference` | No | Reference lines/areas |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `loading` | `loading=true` | Skeleton with shimmer |
| `empty` | `data.length === 0` | "No data available" |
| `error` | `error` prop | Alert + retry |
| `animating` | Mount/update | Staggered entry |
| `interactive` | Hover/Focus | Highlight, tooltip |

---

## Accessibility

- **Role**: `img` with `aria-label` (title + summary)
- **Keyboard**: Tab to chart, arrows navigate data points
- **Screen Reader**: Table alternative in `aria-describedby`
- **Color**: Not color-only (patterns + labels)
- **Focus**: Visible focus ring on data points

---

## Loading

- **Skeleton**: Chart outline with shimmer
- **Delay**: 200ms before showing skeleton

---

## Errors

- **No Data**: "No data available for selected filters"
- **Fetch Failed**: "Failed to load chart data — [Retry]"

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus chart |
| `←/→` | Navigate data points |
| `↑/↓` | Navigate series |
| `Enter` | Show tooltip |
| `Escape` | Close tooltip |

---

## Mobile

- **< 640px**: Simplified (no legend, smaller)
- **Touch**: Tap for tooltip
- **Pan**: Horizontal pan for wide charts
- **Pinch**: Zoom (optional)

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `chart_view` | `type`, `series_count`, `data_points` |
| `chart_interaction` | `type`, `action` (hover, click, zoom) |
| `chart_export` | `type`, `format` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: ['chart', 'pipeline', { agency, zone, period }],
  select: (response) => ({
    data: response.monthly_data,
    meta: response.meta
  })
});
```

---

## Dependencies

- `recharts` (core)
- `date-fns` (date formatting)
- `lucide-react`: `Download`, `Maximize`, `Info`, `AlertTriangle`

---

## Usage Examples

```tsx
// Line chart - pipeline trend
<LineChart
  data={pipelineData}
  xKey="month"
  yKeys={['live_tenders', 'awarded_tenders', 'cancelled_tenders']}
  xLabel="Month"
  yLabel="Count"
  title="Tender Pipeline Trend"
  colors={['#3B82F6', '#22C55E', '#EF4444']}
  referenceLines={[{ value: 100, label: 'Target', stroke: '#6B7280' }]}
  height={400}
/>

// Stacked bar - agency spend
<StackedBarChart
  data={agencySpend}
  xKey="agency"
  yKeys={['Q1', 'Q2', 'Q3', 'Q4']}
  xLabel="Agency"
  yLabel="Spend (BDT)"
  title="Quarterly Agency Spend"
  layout="horizontal"
/>

// Donut - win probability
<DonutChart
  data={[{ name: 'Won', value: 71 }, { name: 'Lost', value: 29 }]}
  xKey="name"
  yKey="value"
  innerRadius={60}
  title="Win Probability"
  colors={['#22C55E', '#EF4444']}
/>

// Radar - contractor profile
<RadarChart
  data={contractorScores}
  xKey="dimension"
  yKeys={['technical', 'financial', 'experience', 'management', 'safety']}
  title="Contractor Capability Radar"
/>

// Composed - dual axis
<ComposedChart
  data={revenueData}
  xKey="month"
  bars={[{ key: 'revenue', name: 'Revenue', color: '#3B82F6' }]}
  lines={[{ key: 'margin', name: 'Margin %', color: '#22C55E', yAxisId: 'right' }]}
  yAxisRight={{ label: 'Margin %' }}
/>
```

---

## Theming

```typescript
// Default color palette
const CHART_COLORS = [
  '#3B82F6',  // primary
  '#22C55E',  // success
  '#F59E0B',  // warning
  '#EF4444',  // danger
  '#8B5CF6',  // purple
  '#06B6D4',  // cyan
  '#F97316',  // orange
  '#EC4899',  // pink
];

// Dark mode (auto via CSS variables)
@media (prefers-color-scheme: dark) {
  :root {
    --chart-grid: #374151;
    --chart-text: #D1D5DB;
    --chart-bg: #1F2937;
  }
}
```

---

## Future Extensions

- [ ] Real-time streaming data
- [ ] Brush/zoom for large datasets
- [ ] Annotations on data points
- [ ] Drill-down (click to detail)
- [ ] Comparative periods (YoY)
- [ ] Export to PNG/SVG/PDF
- [ ] Chart builder UI
- [ ] Accessibility table fallback