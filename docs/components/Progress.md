# Progress Component Contract

**Package**: `shared/ui`  
**Type**: Feedback Component  
**Stability**: Stable  

---

## Purpose

Visual progress indicator for linear and circular progress. Used for file uploads, agent execution, report generation, and multi-step workflows.

---

## Props

```typescript
interface ProgressProps {
  /** Progress value (0-100) */
  value: number;
  /** Max value */
  max?: number; // default: 100
  /** Show label */
  showLabel?: boolean;
  /** Label format */
  labelFormat?: (value: number, max: number) => string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Variant */
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  /** Show stripes */
  striped?: boolean;
  /** Animated stripes */
  animated?: boolean;
  /** Custom className */
  className?: string;
}
```

---

## Circular Progress Props

```typescript
interface CircularProgressProps {
  /** Progress value (0-100) */
  value: number;
  /** Size in pixels */
  size?: number; // default: 48
  /** Stroke width */
  strokeWidth?: number; // default: 4
  /** Show value label */
  showValue?: boolean;
  /** Custom label */
  label?: React.ReactNode;
  /** Variant */
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  /** Track color */
  trackColor?: string;
  /** Animated */
  animated?: boolean;
  /** ClassName */
  className?: string;
}
```

---

## State

| State | Linear | Circular |
|-------|--------|----------|
| `idle` | Empty bar | Empty ring |
| `progress` | Filled bar | Filled ring |
| `complete` | Full, success color | Full, checkmark |
| `indeterminate` | Animated bar | Spinning ring |
| `error` | Danger color | Error color + icon |

---

## Accessibility

- **Role**: `progressbar`
- **ARIA**: `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- **Label**: `aria-label` or `aria-labelledby`
- **Screen Reader**: Announces percentage changes

---

## Loading

- **Indeterminate**: Animated bar/ring
- **Delay**: Show after 500ms if not complete

---

## Mobile

- **Linear**: Full width, min height 4px
- **Circular**: Min 32px, max 120px
- **Touch**: No interaction

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `progress_change` | `value`, `type` |
| `progress_complete` | `duration_ms` |

---

## Usage Examples

```tsx
// Linear upload progress
<Progress
  value={uploadProgress}
  showLabel
  labelFormat={(v) => `${v}% uploaded`}
  size="md"
  variant={uploadProgress === 100 ? 'success' : 'default'}
/>

// Circular agent execution
<CircularProgress
  value={executionProgress}
  size={64}
  strokeWidth={6}
  animated
  label={
    <Text size="sm" weight="medium">
      {executionProgress}%
    </Text>
  }
/>

// Multi-step wizard
<Flex gap={4} className="w-full">
  {steps.map((step, i) => (
    <Flex flexDir="column" align="center" key={step.id}>
      <CircularProgress
        size={40}
        value={i < currentStep ? 100 : i === currentStep ? stepProgress : 0}
        variant={i < currentStep ? 'success' : i === currentStep ? 'default' : 'default'}
      >
        {i + 1}
      </CircularProgress>
      <Text size="xs" className={i === currentStep ? 'weight-medium' : ''}>
        {step.label}
      </Text>
    </Flex>
  ))}
</Flex>
```

---

## Future Extensions

- [ ] Step progress with labels
- [ ] Time remaining estimation
- [ ] Pause/resume controls
- [ ] Segmented progress
- [ ] Background sync indicator