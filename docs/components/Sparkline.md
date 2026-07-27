# Sparkline Component Contract

**Package**: `widgets/charts`  
**Type**: Data Visualization Component  
**Stability**: Stable  

---

## Purpose

Inline miniature chart for trend visualization in KPI cards, tables, and dashboards. No axes, minimal UI.

---

## Props

```typescript
interface SparklineProps {
  /** Data points */
  data: number[];
  /** Chart type */
  type?: 'line' | 'area' | 'bar';
  /** Width */
  width?: number; // default: 120
  /** Height */
  height?: number; // default: 40
  /** Line color */
  color?: string; // default: brand-500
  /** Fill color (area) */
  fillColor?: string;
  /** Show points */
  showPoints?: boolean;
  /** Point size */
  pointSize?: number; // default: 3
  /** Show last value label */
  showValue?: boolean;
  /** Value formatter */
  formatValue?: (value: number) => string;
  /** Reference line */
  referenceValue?: number;
  /** Reference line color */
  referenceColor?: string;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| — | — | Self-contained |

---

## State

| State | Visual |
|-------|--------|
| `default` | Rendered chart |
| `empty` | Placeholder line |
| `loading` | Skeleton shimmer |

---

## Accessibility

- **Role**: `img` with `aria-label` describing trend
- **Label**: "Sparkline showing [trend] over [period], current value [value]"
- **Keyboard**: Not focusable (decorative)

---

## Usage Examples

```tsx
// Basic line
<Sparkline
  data={[12, 15, 13, 17, 19, 16, 22]}
  color="#3B82F6"
/>

// Area with fill
<Sparkline
  data={revenueData}
  type="area"
  fillColor="rgba(34, 197, 94, 0.1)"
  color="#22C55E"
  showValue
  formatValue={v => formatCurrency(v)}
/>

// With reference line
<Sparkline
  data={monthlyTrend}
  referenceValue={target}
  referenceColor="#EF4444"
  showValue
/>

// Bar chart
<Sparkline
  data={quarterlyData}
  type="bar"
  color="#8B5CF6"
/>

// In KPI card
<KpiCard
  label="Revenue"
  value={formatCurrency(4.5M)}
  trend={{ value: 12.3, isPositive: true }}
  sparkline={<Sparkline data={monthlyRevenue} type="area" color="#22C55E" fillColor="rgba(34,197,94,0.1)" />}
/>

// In table
<TableColumn
  key="trend"
  header="Trend"
  accessor="trendData"
  render={(data) => (
    <Sparkline
      data={data}
      width={100}
      height={30}
      type="line"
      color="#3B82F6"
    />
  )}
/>

// Multiple colors for comparison
<Flex gap={4}>
  <Sparkline data={actual} color="#3B82F6" width={80} />
  <Sparkline data={target} color="#9CA3AF" width={80} />
</Flex>
```

---

## Color Guidelines

| Context | Color | CSS Variable |
|---------|-------|--------------|
| Primary | Blue | `--color-brand-500` |
| Success | Green | `--color-success-500` |
| Warning | Amber | `--color-warning-500` |
| Danger | Red | `--color-danger-500` |
| Neutral | Gray | `--color-gray-500` |

---

## Performance

- **Points**: Max 100 (auto-sample if more)
- **Render**: SVG (scalable)
- **Animation**: CSS transition on data change (300ms)

---

## Future Extensions

- [ ] Tooltip on hover
- [ ] Animation on mount
- [ ] Multiple series overlay
- [ ] Brush/zoom for detail
- [ ] Export to SVG/PNG