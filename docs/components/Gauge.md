# Gauge Component Contract

**Package**: `widgets/charts`  
**Type**: Data Visualization Component  
**Stability**: Stable  

---

## Purpose

Circular or semi-circular gauge for displaying single metrics with thresholds. Used for win probability, SLT risk, capacity utilization, and budget consumption.

---

## Props

```typescript
interface GaugeProps {
  /** Current value (0-100) */
  value: number;
  /** Max value */
  max?: number; // default: 100
  /** Min value */
  min?: number; // default: 0
  /** Gauge type */
  type?: 'full' | 'semi' | 'arc';
  /** Size in pixels */
  size?: number; // default: 120
  /** Stroke width */
  strokeWidth?: number; // default: 8
  /** Color segments */
  segments?: GaugeSegment[];
  /** Show value label */
  showValue?: boolean; // default: true
  /** Value formatter */
  formatValue?: (value: number) => string;
  /** Label below gauge */
  label?: string;
  /** Sub-label */
  subLabel?: string;
  /** Animation duration (ms) */
  animationDuration?: number; // default: 1000
  /** Custom className */
  className?: string;
}

interface GaugeSegment {
  /** Start value */
  from: number;
  /** End value */
  to: number;
  /** Color */
  color: string;
  /** Label */
  label?: string;
}
```

---

## Default Segments (Win Probability)

```typescript
const WIN_PROBABILITY_SEGMENTS = [
  { from: 0, to: 30, color: '#EF4444', label: 'Critical' },    // Red
  { from: 30, to: 50, color: '#F59E0B', label: 'Low' },         // Amber
  { from: 50, to: 70, color: '#3B82F6', label: 'Medium' },      // Blue
  { from: 70, to: 85, color: '#22C55E', label: 'High' },        // Green
  { from: 85, to: 100, color: '#10B981', label: 'Very High' }   // Emerald
];
```

---

## Default Segments (SLT Risk)

```typescript
const SLT_RISK_SEGMENTS = [
  { from: 0, to: 20, color: '#22C55E', label: 'Safe' },        // Green
  { from: 20, to: 50, color: '#3B82F6', label: 'Moderate' },    // Blue
  { from: 50, to: 70, color: '#F59E0B', label: 'Elevated' },    // Amber
  { from: 70, to: 100, color: '#EF4444', label: 'Critical' }    // Red
];
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `label` | No | Custom center label |
| `needle` | No | Custom needle/pointer |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `idle` | Default | Static segments |
| `animating` | Value change | Smooth arc animation |
| `loading` | Data fetching | Spinner in center |

---

## Accessibility

- **Role**: `img` with `aria-label`
- **Label**: "Gauge showing [value]%, [label], [segment label]"
- **Keyboard**: Not focusable (decorative)

---

## Usage Examples

```tsx
// Win probability
<Gauge
  value={71}
  label="Win Probability"
  subLabel="Based on 45 similar tenders"
  segments={WIN_PROBABILITY_SEGMENTS}
  size={160}
  strokeWidth={12}
/>

// SLT Risk
<Gauge
  value={65}
  label="SLT Risk"
  subLabel="Score: 65%"
  segments={SLT_RISK_SEGMENTS}
  type="semi"
  size={140}
  formatValue={v => `${v}%`}
/>

// Capacity utilization
<Gauge
  value={78}
  max={100}
  label="Capacity"
  subLabel="78% utilized"
  segments={[
    { from: 0, to: 50, color: '#22C55E', label: 'Available' },
    { from: 50, to: 80, color: '#F59E0B', label: 'Moderate' },
    { from: 80, to: 100, color: '#EF4444', label: 'Critical' }
  ]}
  type="arc"
  size={120}
  strokeWidth={10}
/>

// Budget consumption
<Gauge
  value={87}
  label="Budget Used"
  subLabel="৳8.7M of ৳10M"
  segments={[
    { from: 0, to: 50, color: '#22C55E', label: 'Safe' },
    { from: 50, to: 75, color: '#3B82F6', label: 'Moderate' },
    { from: 75, to: 90, color: '#F59E0B', label: 'Warning' },
    { from: 90, to: 100, color: '#EF4444', label: 'Critical' }
  ]}
  showValue
  formatValue={v => `${v}%`}
  size={150}
/>

// Compact (dashboard widget)
<Gauge
  value={68}
  size={80}
  strokeWidth={6}
  showValue
  label="Win Rate"
  segments={WIN_PROBABILITY_SEGMENTS}
/>
```

---

## Type Variants

```tsx
// Full circle
<Gauge type="full" value={75} />

// Semi-circle (default)
<Gauge type="semi" value={75} />

// Arc (custom angle)
<Gauge type="arc" value={75} />
```

---

## Animation

```tsx
<Gauge
  value={animatedValue}
  animationDuration={1500}
  // Easing: ease-out-cubic
/>
```

---

## Future Extensions

- [ ] Needle pointer (analog style)
- [ ] Multiple pointers (current vs target)
- [ ] Gradient segments
- [ ] Threshold alerts (pulse animation)
- [ ] Historical trend overlay
- [ ] Clickable segments (drill-down)
- [ ] Accessibility table fallback