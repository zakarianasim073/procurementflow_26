# ConfidenceBadge Component Contract

**Package**: `shared/ui`  
**Type**: Status Indicator Component  
**Stability**: Stable  

---

## Purpose

Displays a confidence score with label, color coding, and optional trend. Used across AI predictions, win probability, compliance checks, and data quality indicators.

---

## Props

```typescript
interface ConfidenceBadgeProps {
  /** Confidence score (0-1) */
  confidence: number;
  /** Show numeric score */
  showScore?: boolean;
  /** Show label (High/Medium/Low) */
  showLabel?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Variant style */
  variant?: 'badge' | 'pill' | 'ring' | 'dot';
  /** Custom thresholds */
  thresholds?: {
    high: number;    // default: 0.85
    medium: number;  // default: 0.65
  };
  /** Tooltip content */
  tooltip?: string;
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
| `prefix` | No | Icon before badge |
| `suffix` | No | Trend indicator after badge |

---

## State

| State | Confidence Range | Visual |
|-------|------------------|--------|
| `high` | ≥ 0.85 | Green (`success`), label "High" |
| `medium` | 0.65–0.84 | Amber (`warning`), label "Medium" |
| `low` | < 0.65 | Red (`danger`), label "Low" |
| `unknown` | `null`/`undefined` | Gray (`muted`), label "N/A" |

---

## Accessibility

- **Role**: `status` with `aria-label="Confidence: [label] [score]%"`
- **Color**: Not color-only — includes label and icon
- **Keyboard**: Focusable if `onClick` provided
- **Screen Reader**: Announces "Confidence [label], [score] percent"

---

## Loading

- **Skeleton**: Pulse animation in badge color
- **Delay**: 100ms

---

## Errors

- **Invalid Score**: Shows "N/A" with warning icon

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus badge |
| `Enter` / `Space` | Trigger `onClick` |

---

## Mobile

- **All sizes**: Responsive text scaling
- **Ring Variant**: 24px → 20px on mobile
- **Pill Variant**: Full text on lg, icon-only on sm

---

## Permissions

| Role | View |
|------|------|
| All | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `confidence_badge_view` | `confidence`, `level`, `variant` |
| `confidence_badge_click` | `confidence`, `level` |

---

## React Query

```typescript
// Used with win probability, SLT risk, model confidence
const { data } = useQuery({
  queryKey: executiveKeys.report(tenderId),
  select: (report) => report.win_prediction.confidence
});
```

---

## Dependencies

- `Tooltip` (for score/label detail)
- `lucide-react`: `CheckCircle2`, `AlertTriangle`, `XCircle`, `HelpCircle`, `TrendingUp`, `TrendingDown`

---

## Variants

### Badge (Default)
```
┌─────────────────┐
│ High  92%  ↑    │
└─────────────────┘
```

### Pill
```
┌──────────────┐
│ ● High 92%   │
└──────────────┘
```

### Ring
```
    92%
  ┌──────┐
  │      │
  └──────┘
  High
```

### Dot
```
● High 92%
```

---

## Threshold Customization

```tsx
// Strict thresholds for compliance
<ConfidenceBadge 
  confidence={0.78} 
  thresholds={{ high: 0.9, medium: 0.75 }} 
/>

// Lenient for exploratory analysis
<ConfidenceBadge 
  confidence={0.55} 
  thresholds={{ high: 0.7, medium: 0.5 }} 
/>
```

---

## Future Extensions

- [ ] Animated confidence ring
- [ ] Historical confidence trend sparkline
- [ ] Calibration curve overlay
- [ ] Uncertainty interval display