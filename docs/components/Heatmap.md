# Heatmap Component Contract

**Package**: `widgets/charts`  
**Type**: Data Visualization Component  
**Stability**: Stable  

---

## Purpose

Matrix visualization for showing intensity across two dimensions. Used for contractor-agency heatmaps, zone-category analysis, and temporal patterns.

---

## Props

```typescript
interface HeatmapProps {
  /** Data matrix */
  data: HeatmapCell[][];
  /** X-axis labels */
  xLabels: string[];
  /** Y-axis labels */
  yLabels: string[];
  /** Color scale */
  colorScale?: ColorScale;
  /** Cell renderer */
  cellRenderer?: (value: number, x: number, y: number) => React.ReactNode;
  /** Cell click handler */
  onCellClick?: (value: number, x: number, y: number, rowLabel: string, colLabel: string) => void;
  /** Show values */
  showValues?: boolean;
  /** Value formatter */
  formatValue?: (value: number) => string;
  /** Color scale legend */
  showLegend?: boolean;
  /** Cell size */
  cellSize?: number; // default: 40
  /** Gap between cells */
  gap?: number; // default: 1
  /** Custom className */
  className?: string;
}

interface HeatmapCell {
  value: number;
  label?: string;
  metadata?: Record<string, any>;
}

interface ColorScale {
  /** Min value */
  min: number;
  /** Max value */
  max: number;
  /** Color stops */
  stops: { value: number; color: string }[];
  /** Missing value color */
  missingColor?: string; // default: gray-200
}
```

---

## Default Color Scales

```typescript
// Sequential (single hue)
const SEQUENTIAL_BLUE = {
  min: 0, max: 100,
  stops: [
    { value: 0, color: '#EFF6FF' },
    { value: 25, color: '#93C5FD' },
    { value: 50, color: '#3B82F6' },
    { value: 75, color: '#1D4ED8' },
    { value: 100, color: '#1E3A8A' }
  ]
};

// Diverging (two hues)
const DIVERGING_RdBu = {
  min: -100, max: 100,
  stops: [
    { value: -100, color: '#67001F' },
    { value: -50, color: '#EF8A62' },
    { value: 0, color: '#F7F7F7' },
    { value: 50, color: '#67A9CF' },
    { value: 100, color: '#2166AC' }
  ]
};

// Sequential green (for positive metrics)
const SEQUENTIAL_GREEN = {
  min: 0, max: 100,
  stops: [
    { value: 0, color: '#F0FDF4' },
    { value: 25, color: '#86EFAC' },
    { value: 50, color: '#22C55E' },
    { value: 75, color: '#15803D' },
    { value: 100, color: '#14532D' }
  ]
};
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `cell` | No | Custom cell content |
| `xAxis` | No | Custom X-axis |
| `yAxis` | No | Custom Y-axis |
| `legend` | No | Custom legend |

---

## State

| State | Visual |
|-------|--------|
| `default` | Colored cells |
| `hover` | Cell highlight, tooltip |
| `selected` | Border highlight |
| `loading` | Skeleton cells |

---

## Accessibility

- **Role**: `img` with `aria-label`
- **Description**: "Heatmap showing [metric] across [rows] by [columns], range [min] to [max]"
- **Keyboard**: Arrow keys navigate cells, Enter selects
- **Color**: Not color-only (values shown on hover/selection)

---

## Usage Examples

```tsx
// Contractor-Agency heatmap
<Heatmap
  data={contractorAgencyMatrix}
  xLabels={agencies}
  yLabels={contractors}
  colorScale={SEQUENTIAL_BLUE}
  showValues
  formatValue={v => v > 0 ? v.toString() : ''}
  onCellClick={(val, x, y, contractor, agency) => {
    openContractorDetail(contractor, agency);
  }}
  cellSize={45}
  showLegend
/>

// Zone-Category analysis
<Heatmap
  data={zoneCategoryMatrix}
  xLabels={categories}
  yLabels={zones}
  colorScale={SEQUENTIAL_GREEN}
  showValues
  formatValue={v => `${v}%`}
  showLegend
  cellSize={50}
  label="Win Rate by Zone & Category"
/>

// Temporal pattern
<Heatmap
  data={monthlyHourlyActivity}
  xLabels={['12am','3am','6am','9am','12pm','3pm','6pm','9pm']}
  yLabels={['Mon','Tue','Wed','Thu','Fri','Sat','Sun']}
  colorScale={SEQUENTIAL_BLUE}
  showValues={false}
  cellSize={35}
  showLegend
  label="Activity by Day & Hour"
/>

// Diverging (positive/negative)
<Heatmap
  data={profitMarginMatrix}
  xLabels={contractors}
  yLabels={projects}
  colorScale={DIVERGING_RdBu}
  showValues
  formatValue={v => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`}
  showLegend
  cellSize={40}
/>
```

---

## Tooltip Content

```tsx
<Heatmap
  // ...
  cellRenderer={(value, x, y) => (
    <Tooltip
      content={
        <Flex flexDir="column" gap={1}>
          <Text weight="medium">{yLabels[y]} × {xLabels[x]}</Text>
          <Text className="text-muted">{metadata?.detail}</Text>
        </Flex>
      }
    >
      <HeatmapCell value={value} />
    </Tooltip>
  )}
/>
```

---

## Legend Component

```tsx
<HeatmapLegend
  colorScale={SEQUENTIAL_BLUE}
  orientation="horizontal"
  width={300}
  showLabels
  labelFormat={v => v === 0 ? '0' : v === 100 ? '100+' : `${v}`}
  position="bottom"
/>
```

---

## Mobile

- **< 640px**: Horizontal scroll, frozen first column
- **Touch**: Tap for tooltip, long-press for context menu
- **Legend**: Collapsible bottom sheet

---

## Future Extensions

- [ ] Clustering (reorder rows/cols)
- [ ] Brush selection (range filter)
- [ ] Hierarchical labels
- [ ] Animation on data change
- [ ] Export to image
- [ ] Clustering dendrogram