# FormField Component Contract

**Package**: `shared/ui`  
**Type**: Form Layout Component  
**Stability**: Stable  

---

## Purpose

Wrapper component for consistent form field layout with label, input, helper text, and error message. Ensures consistent spacing and accessibility across all forms.

---

## Props

```typescript
interface FormFieldProps {
  /** Label text */
  label?: string;
  /** Required indicator */
  required?: boolean;
  /** Helper text */
  helperText?: string;
  /** Error message */
  error?: string;
  /** Input element */
  children: React.ReactElement;
  /** Label position */
  labelPosition?: 'top' | 'left'; // default: 'top'
  /** Full width */
  fullWidth?: boolean;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `children` | **Yes** | Input component (Input, Select, Textarea, etc.) |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Normal label, no error |
| `error` | `error` prop | Red label, error message |
| `disabled` | Input disabled | Muted label |
| `required` | `required=true` | Asterisk in label |

---

## Accessibility

- **Label**: `htmlFor` matches input `id`
- **Error**: `aria-describedby` links to error
- **Helper**: `aria-describedby` links to helper
- **Required**: `aria-required` on input

---

## Keyboard

Not applicable (layout component)

---

## Mobile

- **Label Top**: Default (stacked)
- **Label Left**: `labelPosition="left"` on ≥ 768px

---

## Permissions

Not applicable

---

## Telemetry

Not applicable

---

## Usage Examples

```tsx
// Basic
<FormField label="Email" required>
  <Input type="email" placeholder="you@company.com" />
</FormField>

// With helper
<FormField label="Tender Value" helperText="In Bangladeshi Taka (BDT)">
  <Input type="number" placeholder="50000000" />
</FormField>

// With error
<FormField label="Deadline" error="Date must be in the future">
  <DatePicker value={date} onChange={setDate} minDate={new Date()} />
</FormField>

// Horizontal layout (desktop)
<FormField label="Zone" labelPosition="left">
  <Select value={zone} onChange={setZone} options={zoneOptions} />
</FormField>

// Multiple fields in row
<Flex gap={4} wrap>
  <FormField label="From" style={{ flex: 1 }}>
    <DatePicker />
  </FormField>
  <FormField label="To" style={{ flex: 1 }}>
    <DatePicker />
  </FormField>
</Flex>

// With custom input
<FormField label="Upload BOQ" helperText="PDF, XLSX, DOCX (max 50MB)">
  <FileUpload accept={['.pdf', '.xlsx', '.docx']} maxSize={50 * 1024 * 1024} />
</FormField>
```

---

## Future Extensions

- [ ] Floating label animation
- [ ] Inline validation messages
- [ ] Tooltip on label
- [ ] Field grouping (fieldset)