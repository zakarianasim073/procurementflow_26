# Alert Component Contract

**Package**: `shared/ui`  
**Type**: Feedback Component  
**Stability**: Stable  

---

## Purpose

Dismissible alert banner for important messages, warnings, errors, and confirmations. Supports actions, icons, and multiple variants.

---

## Props

```typescript
interface AlertProps {
  /** Alert variant */
  variant?: 'info' | 'success' | 'warning' | 'danger';
  /** Title */
  title?: string;
  /** Description */
  children: React.ReactNode;
  /** Dismissible */
  dismissible?: boolean;
  /** Dismiss handler */
  onDismiss?: () => void;
  /** Show icon */
  showIcon?: boolean; // default: true
  /** Action button */
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  };
  /** Custom className */
  className?: string;
}
```

---

## Variants

| Variant | Color | Icon | Use Case |
|---------|-------|------|----------|
| `info` | Blue | `Info` | General info, tips |
| `success` | Green | `CheckCircle` | Completion, saved |
| `warning` | Amber | `AlertTriangle` | Caution, near limits |
| `danger` | Red | `XCircle` | Errors, critical issues |

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `icon` | No | Custom icon |
| `action` | No | Custom action button |
| `close` | No | Custom close button |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Full banner |
| `dismissing` | Click close | Fade out + slide up |
| `dismissed` | Animation end | Removed from DOM |

---

## Accessibility

- **Role**: `alert` (assertive) or `status` (polite)
- **Live Region**: `aria-live="assertive"` for danger, `polite` otherwise
- **Dismiss**: `aria-label="Dismiss"`
- **Action**: `aria-label="[label]"`

---

## Keyboard

| Key | Action |
|-----|--------|
| `Escape` | Dismiss (if dismissible) |
| `Tab` | Focus action/close |
| `Enter` / `Space` | Activate action |

---

## Usage Examples

```tsx
// Basic info
<Alert variant="info" title="New Feature">
  BOQ comparison now supports PWD rates.
</Alert>

// Dismissible warning
<Alert 
  variant="warning" 
  title="Quota Alert" 
  dismissible 
  onDismiss={handleDismiss}
>
  You've used 85% of your monthly API quota.
  <Alert.Action label="Upgrade" onClick={handleUpgrade} />
</Alert>

// Error with action
<Alert 
  variant="danger" 
  title="Upload Failed" 
  action={{ label: 'Retry', onClick: handleRetry }}
>
  The PDF file could not be processed. Please check the format.
</Alert>

// Success
<Alert variant="success" title="Report Generated">
  Your rate analysis report is ready for download.
  <Alert.Action label="Download" onClick={handleDownload} />
</Alert>

// Without icon
<Alert variant="info" showIcon={false}>
  Maintenance scheduled for tonight 2-4 AM.
</Alert>
```

---

## Future Extensions

- [ ] Toast-style (auto-dismiss)
- [ ] Stacked alerts (multiple)
- [ ] Progress indicator
- [ ] Link action