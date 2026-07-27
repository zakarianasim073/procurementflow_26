# Input Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Text input field with label, validation, helper text, and icon support. Used across all forms in the application.

---

## Props

```typescript
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Input label */
  label?: string;
  /** Helper text below input */
  helperText?: string;
  /** Error message (shows error state) */
  error?: string;
  /** Left icon */
  leftIcon?: React.ReactNode;
  /** Right icon */
  rightIcon?: React.ReactNode;
  /** Right element (e.g., clear button) */
  rightElement?: React.ReactNode;
  /** Input size */
  size?: 'sm' | 'md' | 'lg';
  /** Full width */
  fullWidth?: boolean;
  /** Required indicator */
  required?: boolean;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| — | — | No slots (self-contained) |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Border `gray-300`, bg White |
| `hover` | Mouse enter | Border `gray-400` |
| `focus` | Keyboard/click | Ring `brand-500`, border `brand-500` |
| `filled` | Has value | Label floats up (optional) |
| `error` | `error` prop | Border `red-500`, red helper |
| `disabled` | `disabled` | BG `gray-100`, cursor not-allowed |
| `readonly` | `readOnly` | Border `gray-200`, no focus ring |

---

## Sizes

| Size | Padding | Font | Height | Label |
|------|---------|------|--------|-------|
| `sm` | `8px 12px` | `text-sm` | 32px | `text-xs` |
| `md` | `10px 14px` | `text-sm` | 40px | `text-sm` |
| `lg` | `12px 16px` | `text-base` | 48px | `text-sm` |

---

## Accessibility

- **Label**: `<label htmlFor>` linked to input
- **Error**: `aria-invalid="true"`, `aria-describedby` error ID
- **Helper**: `aria-describedby` helper ID
- **Required**: `aria-required`, asterisk in label
- **Keyboard**: Standard input behavior

---

## Loading

Not applicable (use `disabled` for pending)

---

## Errors

- **Inline**: Red border, error text below, icon in rightIcon
- **Clear**: Click right clear button or re-type

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus |
| `Enter` | Submit form (if in form) |
| `Escape` | Blur (optional) |

---

## Mobile

- **Input Type**: Correct `type` for keyboard (email, tel, number)
- **Height**: Min 44dp
- **Font**: 16px prevents zoom on iOS

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `input_change` | `field_name`, `length`, `error` |
| `input_blur` | `field_name`, `valid` |
| `input_error` | `field_name`, `error_type` |

---

## React Query

Not applicable (form state via React Hook Form / Zod)

---

## Dependencies

- `Label` (label component)
- `HelperText` (helper/error text)
- `lucide-react`: `X` (clear), `AlertCircle` (error)

---

## Usage Examples

```tsx
// Basic with label
<Input
  label="Email"
  type="email"
  placeholder="you@company.com"
  helperText="We'll never share your email"
/>

// With validation error
<Input
  label="Tender Value"
  type="number"
  error="Must be greater than 0"
  leftIcon={<DollarSign />}
/>

// With right action
<Input
  label="Search"
  placeholder="Search tenders..."
  rightElement={
    <Button variant="ghost" size="icon">
      <Search />
    </Button>
  }
/>

// Password with toggle
<Input
  label="Password"
  type={showPassword ? 'text' : 'password'}
  rightElement={
    <Button variant="ghost" size="icon" onClick={toggleShow}>
      {showPassword ? <EyeOff /> : <Eye />}
    </Button>
  }
/>
```

---

## Future Extensions

- [ ] Floating label animation
- [ ] Character count
- [ ] Masked input (phone, currency)
- [ ] Auto-complete integration
- [ ] Multi-line textarea variant