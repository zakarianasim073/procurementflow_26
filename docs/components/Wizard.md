# Wizard Component Contract

**Package**: `widgets/forms`  
**Type**: Form Component  
**Stability**: Stable  

---

## Purpose

Multi-step form wizard with validation, branching logic, persistence, and progress tracking. Used for tender submission, report generation, and complex configuration workflows.

---

## Props

```typescript
interface WizardProps {
  /** Steps configuration */
  steps: WizardStep[];
  /** Initial step index */
  initialStep?: number; // default: 0
  /** Step change handler */
  onStepChange?: (step: number, direction: 'next' | 'back') => void;
  /** Next handler (validation) */
  onNext?: (currentStep: number, formData: any) => Promise<boolean> | boolean;
  /** Back handler */
  onBack?: (currentStep: number, formData: any) => void;
  /** Submit handler (last step) */
  onSubmit?: (formData: any) => Promise<boolean> | boolean;
  /** Step validation */
  validateStep?: (stepIndex: number, formData: any) => Promise<ValidationResult> | ValidationResult;
  /** Persist form data */
  persist?: boolean; // default: true
  /** Storage key */
  storageKey?: string; // default: 'wizard-{componentId}'
  /** Show progress bar */
  showProgress?: boolean; // default: true
  /** Allow click navigation */
  clickableSteps?: boolean; // default: true
  /** Custom className */
  className?: string;
}

interface WizardStep {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  /** Validation function */
  validate?: (formData: any) => Promise<ValidationResult> | ValidationResult;
  /** Optional step */
  optional?: boolean;
  /** Skip condition */
  skipWhen?: (formData: any) => boolean;
  /** Custom content */
  content: React.ReactNode | ((formData: any, onChange: (data: any) => void) => React.ReactNode);
  /** Step-level actions */
  actions?: {
    label: string;
    onClick: (formData: any) => void;
    variant?: 'primary' | 'secondary' | 'ghost';
  }[];
}

interface ValidationResult {
  valid: boolean;
  errors?: Record<string, string>;
  warnings?: Record<string, string>;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom header (logo, title) |
| `footer` | No | Custom footer actions |
| `sidebar` | No | Custom sidebar (progress, help) |
| `stepContent` | No | Custom step content wrapper |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `idle` | Initial | Step 1 active |
| `validating` | `onNext` | Spinner in next button |
| `validated` | Success | Next step active |
| `error` | Validation failed | Error messages, stay on step |
| `submitting` | `onSubmit` | Spinner in submit |
| `completed` | `onSubmit` success | Completion screen |
| `dirty` | Unsaved changes | Warning on leave |

---

## Accessibility

- **Role**: `navigation` with `aria-label="Wizard"`
- **Steps**: `role="tab"` with `aria-selected`
- **Panels**: `role="tabpanel"` with `aria-labelledby`
- **Progress**: `aria-label="Step X of Y"`
- **Keyboard**: Arrow keys, Home/End, Enter
- **Screen Reader**: Announces step changes, errors

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate fields / buttons |
| `Enter` | Submit / Next |
| `Escape` | Cancel / Back |
| `Arrow Left/Right` | Previous/Next step (when focused on stepper) |
| `Home` / `End` | First/Last step |
| `Ctrl+Enter` | Submit (any step) |

---

## Loading

- **Step Validation**: Spinner in Next button
- **Submission**: Full-page or button spinner
- **Persistence**: Auto-save indicator

---

## Persistence

```typescript
// Auto-save to localStorage
const STORAGE_KEY = `wizard-${storageKey}`;

const saveState = (step: number, data: any) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    step,
    data,
    timestamp: Date.now()
  }));
};

const loadState = () => {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    const { step, data, timestamp } = JSON.parse(stored);
    // Expire after 7 days
    if (Date.now() - timestamp < 7 * 24 * 60 * 60 * 1000) {
      return { step, data };
    }
  }
  return null;
};
```

---

## Usage Examples

```tsx
// Tender submission wizard
<Wizard
  steps={[
    {
      id: 'basic',
      label: 'Basic Info',
      icon: <InfoIcon />,
      validate: (data) => validateBasicInfo(data),
      content: <BasicInfoForm />
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: <FileIcon />,
      validate: (data) => validateDocuments(data),
      content: <DocumentUploadForm />
    },
    {
      id: 'pricing',
      label: 'Pricing',
      icon: <DollarSign />,
      validate: (data) => validatePricing(data),
      content: <PricingForm />
    },
    {
      id: 'review',
      label: 'Review & Submit',
      icon: <CheckCircle />,
      content: <ReviewSummary />
    }
  ]}
  onNext={async (step, data) => {
    const valid = await steps[step].validate?.(data);
    if (!valid?.valid) return false;
    return true;
  }}
  onSubmit={async (data) => {
    const res = await submitTender(data);
    return res.success;
  }}
  persist
  storageKey="tender-submission"
/>

// Report generation wizard
<Wizard
  steps={[
    { id: 'template', label: 'Template', content: <TemplateSelector /> },
    { id: 'data', label: 'Data Selection', content: <DataSelector /> },
    { id: 'format', label: 'Format', content: <FormatOptions /> },
    { id: 'schedule', label: 'Schedule', optional: true, content: <ScheduleOptions /> },
    { id: 'generate', label: 'Generate', content: <GeneratePreview /> }
  ]}
  initialStep={0}
  onNext={async (step, data) => {
    if (step === 0 && !data.templateId) return false;
    if (step === 1 && !data.dataSources?.length) return false;
    return true;
  }}
  onSubmit={async (data) => {
    const job = await generateReport(data);
    return job.success;
  }}
/>

// Agent pipeline wizard
<Wizard
  steps={[
    { id: 'config', label: 'Configure', content: <AgentConfig /> },
    { id: 'input', label: 'Input Data', content: <InputSelector /> },
    { id: 'run', label: 'Execute', content: <ExecutionMonitor /> },
    { id: 'results', label: 'Results', content: <ResultsViewer /> }
  ]}
  onNext={async (step, data) => {
    if (step === 1 && !data.inputData) return false;
    if (step === 2 && data.status !== 'completed') return false;
    return true;
  }}
  onSubmit={async (data) => {
    // Save pipeline
    return true;
  }}
  clickableSteps={false} // Sequential only
  showProgress
/>
```

---

## Branching Logic

```tsx
const steps = [
  {
    id: 'type',
    label: 'Report Type',
    content: <ReportTypeSelector />
  },
  {
    id: 'tender-details',
    label: 'Tender Details',
    skipWhen: (data) => data.reportType !== 'tender',
    content: <TenderDetailForm />
  },
  {
    id: 'contractor-details',
    label: 'Contractor Details',
    skipWhen: (data) => data.reportType !== 'contractor',
    content: <ContractorDetailForm />
  },
  {
    id: 'common',
    label: 'Common Settings',
    content: <CommonSettings />
  }
];
```

---

## Validation Result

```typescript
interface ValidationResult {
  valid: boolean;
  errors: Record<string, string>;      // Field-level errors
  warnings: Record<string, string>;    // Field-level warnings
  globalErrors?: string[];             // Form-level errors
  globalWarnings?: string[];           // Form-level warnings
}
```

---

## Future Extensions

- [ ] Branching wizard (conditional steps)
- [ ] Parallel steps (concurrent)
- [ ] Step dependencies
- [ ] Auto-save to server
- [ ] Collaborative editing
- [ ] Step time tracking
- [ ] Resume from any step
- [ ] A/B testing variants