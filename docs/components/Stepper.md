# Stepper Component Contract

**Package**: `shared/ui`  
**Type**: Navigation Component  
**Stability**: Stable  

---

## Purpose

Multi-step wizard navigation for complex workflows like tender submission, report generation, and agent pipeline execution.

---

## Props

```typescript
interface StepperProps {
  /** Steps configuration */
  steps: Step[];
  /** Current step index (0-based) */
  currentStep: number;
  /** Step change handler */
  onStepChange: (step: number) => void;
  /** Next handler (with validation) */
  onNext?: () => Promise<boolean> | boolean;
  /** Back handler */
  onBack?: () => void;
  /** Submit handler (last step) */
  onSubmit?: () => Promise<boolean> | boolean;
  /** Orientation */
  orientation?: 'horizontal' | 'vertical';
  /** Show step numbers */
  showNumbers?: boolean;
  /** Allow click navigation */
  clickable?: boolean;
  /** Custom className */
  className?: string;
}

interface Step {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  /** Validation function */
  validate?: () => Promise<boolean> | boolean;
  /** Optional step */
  optional?: boolean;
  /** Disabled */
  disabled?: boolean;
  /** Custom content (rendered in step panel) */
  content?: React.ReactNode;
}
```

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `completed` | `onNext` success | Checkmark, muted |
| `current` | Active | Highlighted, expanded |
| `pending` | Future | Muted, disabled |
| `error` | Validation failed | Red border, alert |
| `optional` | `optional=true` | "Optional" badge |
| `disabled` | `disabled=true` | Muted, not clickable |

---

## Accessibility

- **Role**: `navigation` with `aria-label="Stepper"`
- **Steps**: `role="tab"` with `aria-selected`
- **Panels**: `role="tabpanel"` with `aria-labelledby`
- **Keyboard**: Arrow keys, Home/End, Enter
- **Screen Reader**: Announces step changes

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Left/Right` | Previous/Next (horizontal) |
| `Arrow Up/Down` | Previous/Next (vertical) |
| `Enter` / `Space` | Activate step |
| `Home` / `End` | First/Last step |
| `Tab` | Enter panel content |

---

## Loading

- **Validation**: Spinner in step indicator
- **Navigation**: Buttons disabled during async

---

## Mobile

- **< 768px**: Vertical stack, full-width
- **Swipe**: Swipe to next/back (optional)
- **Progress**: Top progress bar

---

## Permissions

| Role | Can Navigate |
|------|--------------|
| All authenticated | ✅ (steps filtered by permission) |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `stepper_change` | `from_step`, `to_step`, `direction` |
| `stepper_complete` | `total_steps`, `duration_ms` |
| `stepper_validation_fail` | `step_id`, `errors` |

---

## React Query

```typescript
// Step validation with server
const validateStep = async (stepId: string, data: any) => {
  const res = await fetch(`/api/validate/${stepId}`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
  return res.ok;
};

<Stepper
  steps={[
    { id: 'info', label: 'Tender Info', validate: () => validateStep('info', formData.info), content: <InfoForm /> },
    { id: 'boq', label: 'BOQ Upload', validate: () => validateStep('boq', formData.boq), content: <BoqUpload /> },
    { id: 'pricing', label: 'Pricing', validate: () => validateStep('pricing', formData.pricing), content: <PricingForm /> },
    { id: 'review', label: 'Review & Submit', content: <ReviewSummary /> }
  ]}
  currentStep={step}
  onStepChange={setStep}
  onNext={async () => await validateStep(steps[step].id, formData)}
  onSubmit={async () => { await submitForm(); return true; }}
  orientation="horizontal"
/>
```

---

## Usage Examples

```tsx
// Horizontal wizard
<Stepper
  steps={[
    { id: 'step1', label: 'Details', content: <DetailsForm /> },
    { id: 'step2', label: 'Documents', content: <DocumentUpload /> },
    { id: 'step3', label: 'Review', content: <ReviewPanel /> }
  ]}
  currentStep={step}
  onStepChange={setStep}
  onNext={async () => await validateCurrentStep()}
  onSubmit={async () => { await submit(); return true; }}
  orientation="horizontal"
/>

// Vertical (sidebar)
<Stepper
  steps={pipelineSteps}
  currentStep={currentStep}
  onStepChange={setCurrentStep}
  orientation="vertical"
  showNumbers
/>

// With validation
<Stepper
  steps={[
    { id: 'tender', label: 'Tender', validate: () => validateTender(), content: <TenderForm /> },
    { id: 'boq', label: 'BOQ', validate: () => validateBoq(), content: <BoqForm /> },
    { id: 'submit', label: 'Submit', content: <SubmitForm /> }
  ]}
  currentStep={step}
  onStepChange={setStep}
  onNext={async () => {
    const valid = await steps[step].validate?.();
    if (!valid) return false;
    return true;
  }}
  onSubmit={async () => { await finalSubmit(); return true; }}
/>
```

---

## Layout

```
Horizontal:
┌─────────────────────────────────────────────────────────────┐
│  1. Details      2. Documents      3. Review      4. Submit │
│  ●───────────────●───────────────●───────────────●────────● │
└─────────────────────────────────────────────────────────────┘
│  [Step Content Panel]                                       │
│                                                             │
│                    [Back]  [Next]  [Submit]                │
└─────────────────────────────────────────────────────────────┘

Vertical:
┌─────────────┬──────────────────────────────────────────────┐
│  1. Details │                                              │
│  ●──────────│  [Step Content Panel]                        │
│  2. BOQ     │                                              │
│  ○──────────│                                              │
│  3. Review  │                                              │
│  ○──────────│                                              │
└─────────────┴──────────────────────────────────────────────┘
```

---

## Future Extensions

- [ ] Branching logic (conditional steps)
- [ ] Step dependencies
- [ ] Auto-save draft
- [ ] Resume from last step
- [ ] Progress persistence
- [ ] Step time tracking