# EmptyState Component Contract

**Package**: `shared/ui`  
**Type**: Feedback Component  
**Stability**: Stable  

---

## Purpose

Illustrated empty state for when content is missing, no results found, or feature not yet available. Provides clear guidance and primary action.

---

## Props

```typescript
interface EmptyStateProps {
  /** Illustration type */
  variant?: 'default' | 'search' | 'filter' | 'create' | 'error' | 'offline' | 'permission';
  /** Title */
  title: string;
  /** Description */
  description?: string;
  /** Primary action */
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  };
  /** Secondary action */
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  /** Custom illustration */
  illustration?: React.ReactNode;
  /** Size */
  size?: 'sm' | 'md' | 'lg';
  /** Custom className */
  className?: string;
}
```

---

## Variants

| Variant | Illustration | Title | Use Case |
|---------|--------------|-------|----------|
| `default` | Inbox | "No items yet" | Generic empty |
| `search` | Magnifying glass | "No results found" | Empty search |
| `filter` | Funnel | "No matches" | Filtered results empty |
| `create` | Plus circle | "Get started" | First-time use |
| `error` | Alert triangle | "Something went wrong" | Error state |
| `offline` | Wifi off | "You're offline" | No connection |
| `permission` | Lock | "Access denied" | No permission |

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `icon` | No | Custom icon (overrides variant) |
| `action` | No | Custom action button |
| `secondary` | No | Custom secondary action |

---

## State

| State | Visual |
|-------|--------|
| `default` | Centered illustration + text + actions |
| `compact` | `size="sm"` - smaller illustration, tighter spacing |

---

## Usage Examples

```tsx
// Default empty
<EmptyState
  title="No tenders yet"
  description="Start by creating your first tender or importing from e-GP"
  action={{ label: 'Create Tender', onClick: () => router.push('/tender/new') }}
/>

// Search empty
<EmptyState
  variant="search"
  title="No tenders found"
  description="Try adjusting your search or filters"
  secondaryAction={{ label: 'Clear filters', onClick: clearFilters }}
/>

// First-time create
<EmptyState
  variant="create"
  title="No BOQ comparisons yet"
  description="Upload a BOQ file to start comparing rates"
  action={{ label: 'Upload BOQ', onClick: () => openUpload() }}
  size="lg"
/>

// Error state
<EmptyState
  variant="error"
  title="Failed to load tenders"
  description="Unable to connect to the server. Please check your connection."
  action={{ label: 'Retry', onClick: refetch }}
  secondaryAction={{ label: 'Work offline', onClick: () => router.push('/offline') }}
/>

// Permission denied
<EmptyState
  variant="permission"
  title="Access restricted"
  description="You don't have permission to view this section"
  action={{ label: 'Request access', onClick: requestAccess }}
/>

// Offline
<EmptyState
  variant="offline"
  title="You're offline"
  description="Changes will sync when you're back online"
  action={{ label: 'Retry connection', onClick: retryConnection }}
/>

// Custom illustration
<EmptyState
  title="No BOQ items"
  description="Upload a BOQ file to see items here"
  illustration={<CustomIllustration />}
  action={{ label: 'Upload BOQ', onClick: openUpload }}
/>

// Compact (for cards)
<Card>
  <EmptyState
    size="sm"
    variant="filter"
    title="No items match"
    description="Try different filters"
  />
</Card>
```

---

## Sizes

| Size | Illustration | Title | Spacing |
|--------|--------------|-------|---------|
| `sm` | 48×48px | `text-base` | Compact |
| `md` | 80×80px | `text-lg` | Default |
| `lg` | 120×120px | `text-xl` | Generous |

---

## Default Illustrations

```typescript
const ILLUSTRATIONS = {
  default: <InboxIcon className="w-16 h-16 text-gray-300" />,
  search: <SearchIcon className="w-16 h-16 text-gray-300" />,
  filter: <FunnelIcon className="w-16 h-16 text-gray-300" />,
  create: <PlusCircleIcon className="w-16 h-16 text-brand-500" />,
  error: <AlertTriangleIcon className="w-16 h-16 text-red-400" />,
  offline: <WifiOffIcon className="w-16 h-16 text-gray-400" />,
  permission: <LockIcon className="w-16 h-16 text-amber-500" />,
};
```

---

## Future Extensions

- [ ] Animated illustrations (Lottie)
- [ ] Personalized empty states
- [ ] Onboarding tour integration
- [ ] Analytics tracking