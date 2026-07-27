# Dialog Component Contract

**Package**: `shared/ui`  
**Type**: Overlay Component  
**Stability**: Stable  

---

## Purpose

Modal dialog for focused interactions, confirmations, forms, and detailed views. Supports multiple sizes, scroll behavior, and accessibility.

---

## Props

```typescript
interface DialogProps {
  /** Open state */
  open: boolean;
  /** Close handler */
  onClose: () => void;
  /** Title */
  title?: string;
  /** Description (announced to screen readers) */
  description?: string;
  /** Size */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** Show close button */
  showClose?: boolean; // default: true
  /** Close on overlay click */
  closeOnOverlayClick?: boolean; // default: true
  /** Close on Escape */
  closeOnEscape?: boolean; // default: true
  /** Disable scroll lock */
  disableScrollLock?: boolean;
  /** Footer actions */
  footer?: React.ReactNode;
  /** Content */
  children: React.ReactNode;
  /** Custom className */
  className?: string;
}
```

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
| `opening` | `open=true` | Fade + slide up |
| `open` | Mounted | Full opacity, centered |
| `closing` | `onClose` | Fade + slide down |
| `loading` | Async action | Spinner in footer |

---

## Accessibility

- **Role**: `dialog` (modal) or `alertdialog` (critical)
- **ARIA**: `aria-labelledby` (title), `aria-describedby` (description)
- **Focus Trap**: Tab cycles within dialog
- **Focus Restoration**: Returns to trigger on close
- **Initial Focus**: First focusable element
- **Screen Reader**: Announces title + description on open

---

## Keyboard

| Key | Action |
|-----|--------|
| `Escape` | Close (if `closeOnEscape`) |
| `Tab` | Next focusable |
| `Shift+Tab` | Previous focusable |
| `Enter` | Submit (if form) |
| `Tab` (last) | Wrap to first |

---

## Loading State

- **Trigger**: Form submit, async action
- **Visual**: Spinner in footer, buttons disabled
- **Min Duration**: 300ms
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
| `dialog_open` | `size`, `title` |
| `dialog_close` | `duration_ms`, `method` (escape, overlay, button) |
| `dialog_submit` | `title`, `duration_ms` |

---

## React Query

```typescript
const { mutate: submit, isLoading } = useMutation(submitForm, {
  onMutate: () => dialogRef.current?.setLoading(true),
  onSettled: () => dialogRef.current?.setLoading(false),
  onSuccess: () => onClose()
});

<Dialog
  ref={dialogRef}
  open={open}
  onClose={() => setOpen(false)}
  title="Create Tender"
  description="Fill in the details to create a new tender"
  size="lg"
  footer={
    <>
      <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
      <Button variant="primary" onClick={handleSubmit} loading={isLoading}>
        Create
      </Button>
    </>
  }
>
  <TenderForm onSubmit={submit} />
</Dialog>
```

---

## Usage Examples

```tsx
// Basic confirmation
<Dialog
  open={showConfirm}
  onClose={() => setShowConfirm(false)}
  title="Delete Tender"
  description="This action cannot be undone."
  size="sm"
  footer={
    <>
      <Button variant="ghost" onClick={() => setShowConfirm(false)}>Cancel</Button>
      <Button variant="destructive" onClick={handleDelete}>Delete</Button>
    </>
  }
>
  Are you sure you want to delete tender 1298004?
</Dialog>

// Form dialog
<Dialog
  open={showForm}
  onClose={() => setShowForm(false)}
  title="New Tender"
  size="lg"
  footer={
    <>
      <Button variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
      <Button variant="primary" onClick={handleSubmit} loading={submitting}>
        Save
      </Button>
    </>
  }
>
  <TenderForm onSubmit={handleSubmit} />
</Dialog>

// Full-screen (mobile)
<Dialog
  open={showDetail}
  onClose={() => setShowDetail(false)}
  title="Tender Details"
  size="full"
>
  <TenderDetailView tenderId={selectedId} />
</Dialog>

// Alert dialog (critical)
<Dialog
  open={showAlert}
  onClose={() => setShowAlert(false)}
  title="Unsaved Changes"
  description="You have unsaved changes that will be lost."
  size="sm"
  footer={
    <>
      <Button variant="ghost" onClick={() => setShowAlert(false)}>Stay</Button>
      <Button variant="primary" onClick={handleLeave}>Leave</Button>
    </>
  }
  role="alertdialog"
>
  Do you want to leave without saving?
</Dialog>
```

---

## Sizes

| Size | Width | Max Height | Use Case |
|------|-------|------------|----------|
| `sm` | 360px | 90vh | Confirmations |
| `md` | 500px | 90vh | Forms |
| `lg` | 720px | 90vh | Complex forms |
| `xl` | 960px | 90vh | Detailed views |
| `full` | 100vw | 100vh | Mobile, detail views |

---

## Future Extensions

- [ ] Stepper dialog (multi-step)
- [ ] Draggable dialog
- [ ] Resizable dialog
- [ ] Nested dialog support
- [ ] Persistent dialog (localStorage)
- [ ] Print stylesheet