# Toast Component Contract

**Package**: `shared/ui`  
**Type**: Notification Component  
**Stability**: Stable  

---

## Purpose

Non-blocking toast notifications for success, error, warning, and info messages. Auto-dismiss with progress bar, action buttons, and stacking.

---

## Props

```typescript
interface ToastProps {
  /** Toast variant */
  variant: 'success' | 'error' | 'warning' | 'info' | 'loading';
  /** Title */
  title: string;
  /** Description */
  description?: string;
  /** Action button */
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  };
  /** Dismissible */
  dismissible?: boolean;
  /** Auto-dismiss duration (ms) */
  duration?: number; // 0 = no auto-dismiss
  /** Progress bar */
  showProgress?: boolean;
  /** Position */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  /** Toast ID */
  id?: string;
  /** Custom className */
  className?: string;
}
```

---

## Toast Container Props

```typescript
interface ToastContainerProps {
  /** Position */
  position?: ToastProps['position'];
  /** Max visible toasts */
  maxToasts?: number; // default: 5
  /** Gap between toasts */
  gap?: number; // default: 8px
  /** Default duration */
  defaultDuration?: number; // default: 5000
  /** Pause on hover */
  pauseOnHover?: boolean; // default: true
  /** Custom className */
  className?: string;
}
```

---

## API (useToast Hook)

```typescript
interface UseToastReturn {
  /** Show toast */
  toast: (props: ToastProps) => string; // returns toast ID
  /** Dismiss specific toast */
  dismiss: (id: string) => void;
  /** Dismiss all */
  dismissAll: () => void;
  /** Update existing toast */
  update: (id: string, props: Partial<ToastProps>) => void;
}
```

---

## Variants

| Variant | Icon | Color | Use Case |
|---------|------|-------|----------|
| `success` | `CheckCircle` | Green | Completed actions |
| `error` | `AlertCircle` | Red | Failures, validation |
| `warning` | `AlertTriangle` | Amber | Warnings, near-limits |
| `info` | `Info` | Blue | General info |
| `loading` | `Loader2` (spin) | Blue | Async operations |

---

## State

| State | Visual |
|-------|--------|
| `entering` | Slide in + fade |
| `visible` | Full opacity |
| `progress` | Progress bar (if enabled) |
| `exiting` | Fade out + slide |
| `removed` | Removed from DOM |

---

## Accessibility

- **Role**: `status` (polite) or `alert` (assertive for errors)
- **Live Region**: `aria-live="polite"` / `aria-live="assertive"`
- **Close Button**: `aria-label="Dismiss"`
- **Action**: `aria-label="[label]"`
- **Keyboard**: Focusable on tab, Escape dismisses

---

## Keyboard

| Key | Action |
|-----|--------|
| `Escape` | Dismiss focused toast |
| `Tab` | Focus close/action buttons |
| `Enter` / `Space` | Activate action |

---

## Mobile

- **Position**: Bottom-center default
- **Width**: Full-width minus margins
- **Swipe**: Swipe right to dismiss
- **Stack**: Bottom-up stacking

---

## Permissions

Not applicable (system notifications)

---

## Telemetry

| Event | Properties |
|-------|------------|
| `toast_show` | `variant`, `title`, `has_action` |
| `toast_dismiss` | `variant`, `method` (auto, manual, swipe) |
| `toast_action_click` | `variant`, `action_label` |

---

## React Query

```typescript
const { toast } = useToast();

// Mutation with toast
const mutation = useMutation(createTender, {
  onMutate: () => toast({ variant: 'loading', title: 'Creating...', duration: 0 }),
  onSuccess: (data) => toast({ variant: 'success', title: 'Created', description: data.name }),
  onError: (error) => toast({ variant: 'error', title: 'Failed', description: error.message })
});
```

---

## Dependencies

- `Portal` (render to container)
- `Transition` (animations)
- `useToast` (context provider)
- `lucide-react`: `CheckCircle`, `AlertCircle`, `AlertTriangle`, `Info`, `Loader2`, `X`, `ChevronRight`

---

## Usage Examples

```tsx
// Basic usage
const { toast } = useToast();

toast({
  variant: 'success',
  title: 'Tender created',
  description: 'Tender 1298004 has been created successfully.',
  duration: 5000
});

// With action
toast({
  variant: 'error',
  title: 'Upload failed',
  description: 'The PDF file could not be processed.',
  action: {
    label: 'Retry',
    onClick: () => handleRetry(fileId)
  }
});

// Loading → Success
const id = toast({ variant: 'loading', title: 'Processing BOQ...', duration: 0 });
// ... later
toast.update(id, { variant: 'success', title: 'BOQ processed', duration: 5000 });

// Promise wrapper
toast.promise(
  fetchTenders(),
  {
    loading: 'Loading tenders...',
    success: 'Tenders loaded',
    error: (err) => `Failed: ${err.message}`
  }
);
```

---

## Container Setup

```tsx
// In App.tsx
import { ToastContainer } from '@/components/ui/Toast';

function App() {
  return (
    <>
      <ToastContainer position="top-right" maxToasts={5} />
      <Router>...</Router>
    </>
  );
}
```

---

## Future Extensions

- [ ] Rich content (JSX in description)
- [ ] Toast groups/categories
- [ ] Persistent toasts (localStorage)
- [ ] Sound notifications
- [ ] Custom icons
- [ ] Progress callbacks