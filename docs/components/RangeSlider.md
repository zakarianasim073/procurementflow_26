# RangeSlider Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Dual-handle range slider for numeric range selection. Used for budget filters, value ranges, date ranges, and percentage thresholds.

---

## Props

```typescript
interface RangeSliderProps {
  /** Selected range */
  value: [number, number];
  /** Change handler */
  onChange: (range: [number, number]) => void;
  /** Minimum value */
  min: number;
  /** Maximum value */
  max: number;
  /** Step increment */
  step?: number; // default: 1
  /** Value labels */
  labels?: {
    min?: string;
    max?: string;
    format?: (value: number) => string;
  };
  /** Marks on track */
  marks?: Record<number, string>;
  /** Disabled */
  disabled?: boolean;
  /** Vertical orientation */
  vertical?: boolean;
  /** Show tooltips */
  tooltips?: boolean; // default: true
  /** Tooltip format */
  tooltipFormat?: (value: number) => string;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `thumb` | No | Custom thumb rendering |
| `track` | No | Custom track rendering |
| `mark` | No | Custom mark rendering |
| `tooltip` | No | Custom tooltip |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Both thumbs at range |
| `active` | Drag thumb | Highlighted track |
| `focus` | Keyboard | Ring on thumb |
| `disabled` | `disabled=true` | Muted, not interactive |

---

## Accessibility

- **Role**: `slider` with `aria-valuemin`, `aria-valuemax`, `aria-valuenow`
- **ARIA**: `aria-orientation`, `aria-label` for each thumb
- **Keyboard**: Full slider navigation
- **Screen Reader**: Announces values on change

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Right/Up` | Increase value |
| `Arrow Left/Down` | Decrease value |
| `Home` | Min value |
| `End` | Max value |
| `Page Up` | +10 steps |
| `Page Down` | -10 steps |
| `Tab` | Next/prev thumb |

---

## Usage Examples

```tsx
// Budget range
<RangeSlider
  value={budgetRange}
  onChange={setBudgetRange}
  min={0}
  max={1_000_000_000}
  step={1_000_000}
  labels={{
    format: (v) => formatCurrency(v)
  }}
  marks={{
    0: '0',
    250_000_000: '250M',
    500_000_000: '500M',
    750_000_000: '750M',
    1_000_000_000: '1B'
  }}
/>

// Percentage
<RangeSlider
  value={discountRange}
  onChange={setDiscountRange}
  min={0}
  max={100}
  step={0.5}
  labels={{
    format: (v) => `${v}%`
  }}
/>

// With custom tooltip
<RangeSlider
  value={dateRange}
  onChange={setDateRange}
  min={Date.now() - 365*24*60*60*1000}
  max={Date.now()}
  tooltips
  tooltipFormat={(ts) => format(new Date(ts), 'MMM d, yyyy')}
/>
```

---

## Vertical Variant

```tsx
<RangeSlider
  vertical
  value={depthRange}
  onChange={setDepthRange}
  min={0}
  max={100}
  labels={{
    format: (v) => `${v}m`
  }}
  className="h-64"
/>
```

---

## Mobile

- Touch drag thumbs
- Tooltip always visible on touch
- Larger hit targets (24px min)

---

## Future Extensions

- [ ] Multiple ranges (multi-thumb)
- [ ] Histogram overlay
- [ ] Logarithmic scale
- [ ] Discrete steps (snap)
- [ ] Keyboard shortcuts display