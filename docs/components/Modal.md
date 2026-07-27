# Modal Component Contract

**Package**: `shared/ui`  
**Type**: Overlay Component  
**Stability**: Stable  

---

## Purpose

Accessible modal dialog for confirmations, forms, and detailed views. Supports multiple sizes, scroll behavior, and nested modals.

---

## Props

```typescript
interface ModalProps {
  /** Open state */
  open: boolean;
  /** Close handler */
  onClose: () => void;
  /** Modal title */
  title?: string;
  /** Description (announced to screen readers) */
  description?: string;
  /** Size */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** Show close button */
  showClose?: boolean;
  /** Close on overlay click */
  closeOnOverlayClick?: boolean;
  /** Close on Escape */
  closeOnEscape?: boolean;
  /** Disable scroll lock */
  disableScrollLock?: boolean;
  /** Footer content */
  footer?: React.ReactNode;
  /** Custom className */
  className?: string;
  /** Children content */
  children: React.ReactNode;
  /** Callback when fully mounted */
  onOpen?: () => void;
  /** Callback when fully closed */
  onClosed?: () => void;
}
```

---

## Sizes

| Size | Width | Max Height | Use Case |
|------|-------|------------|----------|
| `sm` | 360px | 90vh | Confirmations |
| `md` | 500px | 90vh | Forms |
| `lg` | 720px | 90vh | Detailed views |
| `xl` | 960px | 90vh | Complex forms |
| `full` | 100vw | 100vh | Full-screen views |

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom header (replaces title) |
| `footer` | No | Action buttons (via prop) |
| `closeButton` | No | Custom close button |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | `open=false` | Hidden |
| `opening` | `open=true` | Fade in + slide up |
| `open` | Mounted | Full opacity |
| `closing` | `onClose` | Fade out + slide down |
| `loading` | Async action | Spinner in footer |

---

## Accessibility

- **Role**: `dialog` (modal) or `alertdialog` (critical)
- **ARIA**: `aria-labelledby` (title), `aria-describedby` (description)
- **Focus Trap**: Tab cycles within modal
- **Focus Restoration**: Returns to trigger on close
- **Initial Focus**: First focusable element or close button
- **Screen Reader**: Announces title + description on open

---

## Keyboard

| Key | Action |
|-----|--------|
| `Escape` | Close (if `closeOnEscape`) |
| `Tab` | Next focusable |
| `Shift+Tab` | Previous focusable |
| `Enter` | Submit (if form) |
| `Arrow Keys` | Navigate within |

---

## Loading State

- **Trigger**: `footer` shows spinner + disabled buttons
- **Duration**: Min 200ms to prevent flash
- **Close**: Disabled during loading

---

## Mobile

- **< 640px**: Full-screen (size ignored)
- **Safe Area**: Respects bottom inset
- **Swipe**: Swipe down to close (optional)
- **Keyboard**: Viewport adjustment

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `modal_open` | `size`, `title` |
| `modal_close` | `duration_ms`, `trigger` (escape, overlay, button) |
| `modal_submit` | `title`, `duration_ms` |

---

## React Query

```typescript
// Form submission in modal
const mutation = useMutation(submitForm, {
  onMutate: () => modalRef.current?.setLoading(true),
  onSettled: () => modalRef.current?.setLoading(false),
  onSuccess: () => onClose()
});
```

---

## Dependencies

- `Portal` (render to body)
- `FocusTrap` (focus management)
- `Transition` (animation)
- `ScrollLock` (body scroll)
- `lucide-react`: `X`, `Loader2`, `CheckCircle`, `AlertCircle`

---

## Usage Examples

```tsx
// Basic confirmation
<Modal
  open={showConfirm}
  onClose={() => setShowConfirm(false)}
  title="Delete Tender"
  description="This action cannot be undone."
  size="sm"
  footer={
    <>
      <Button variant="ghost" onClick={() => setShowConfirm(false)}>
        Cancel
      </Button>
      <Button variant="destructive" onClick={handleDelete}>
        Delete
      </Button>
    </>
  }
>
  Are you sure you want to delete this tender?
</Modal>

// Form modal
<Modal
  open={showForm}
  onClose={() => setShowForm(false)}
  title="New Tender"
  size="lg"
  footer={
    <>
      <Button variant="secondary" onClick={() => setShowForm(false)}>
        Cancel
      </Button>
      <Button variant="primary" onClick={handleSubmit} loading={submitting}>
        Create
      </Button>
    </>
  }
>
  <TenderForm onSubmit={handleSubmit} />
</Modal>

// Full-screen view
<Modal
  open={showDetail}
  onClose={() => setShowDetail(false)}
  title="Tender Details"
  size="full"
>
  <TenderDetailView tenderId={selectedId} />
</Modal>
```

---

## Future Extensions

- [ ] Stepper modal (multi-step)
- [ ] Drawer variant (side panel)
- [ ] Nested modal stack
- [ ] Auto-focus management
- [ ] Print stylesheet
- [ ] Server-side rendering support