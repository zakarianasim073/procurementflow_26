# Breadcrumb Component Contract

**Package**: `shared/ui`  
**Type**: Navigation Component  
**Stability**: Stable  

---

## Purpose

Hierarchical breadcrumb navigation showing current location within the app structure. Supports collapsible segments on mobile and custom separators.

---

## Props

```typescript
interface BreadcrumbProps {
  /** Breadcrumb items */
  items: BreadcrumbItem[];
  /** Separator */
  separator?: React.ReactNode; // default: ChevronRight
  /** Max visible items before collapsing */
  maxItems?: number; // default: 5
  /** Collapsed items label */
  collapsedLabel?: string; // default: "..." 
  /** Custom item renderer */
  renderItem?: (item: BreadcrumbItem, index: number, isLast: boolean) => React.ReactNode;
  /** Custom className */
  className?: string;
}

interface BreadcrumbItem {
  /** Display label */
  label: string;
  /** Href (makes it a link) */
  href?: string;
  /** Click handler (alternative to href) */
  onClick?: () => void;
  /** Icon */
  icon?: React.ReactNode;
  /** Disabled state */
  disabled?: boolean;
  /** Current page (no link) */
  current?: boolean;
  /** Tooltip */
  tooltip?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `separator` | No | Custom separator |
| `ellipsis` | No | Collapsed items indicator |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Full or collapsed |
| `hover` | Mouse enter item | Underline (links) |
| `focus` | Keyboard | Ring outline |
| `disabled` | `disabled=true` | Muted, not clickable |
| `current` | `current=true` | Bold, aria-current="page" |

---

## Accessibility

- **Role**: `navigation` with `aria-label="Breadcrumb"`
- **List**: `ol` with `aria-label="Breadcrumb"`
- **Items**: `li` with `aria-current="page"` for current
- **Links**: `a` with `href`
- **Buttons**: `button` for onClick items
- **Ellipsis**: `button` with `aria-label="Show hidden breadcrumbs"`

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate items |
| `Enter` / `Space` | Activate link/button |
| `Arrow Left/Right` | Navigate (when focused) |

---

## Mobile

- **< 640px**: Collapse to first + last + ellipsis
- **Ellipsis**: Opens popover with hidden items
- **Touch**: 44×44mm tap targets
- **Ellipsis Popover**: Bottom sheet on mobile

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `breadcrumb_click` | `index`, `label`, `href` |

---

## React Query

```typescript
// Breadcrumbs typically from router context
import { useLocation, useRoutes } from 'react-router-dom';

function Breadcrumbs() {
  const location = useLocation();
  const itemsFromPath(location.pathname);
  // ...
}
```

---

## Dependencies

- `Popover` (collapsed items)
- `Tooltip` (item tooltips)
- `lucide-react`: `ChevronRight`, `Home`, `MoreHorizontal`, `ChevronDown`

---

## Usage Examples

```tsx
// Basic
<Breadcrumb
  items={[
    { label: 'Home', href: '/', icon: <Home /> },
    { label: 'Tenders', href: '/tender' },
    { label: 'BOQ Comparison', href: '/tender/boq' },
    { label: 'Tender 1298004', current: true }
  ]}
/>

// With icons and tooltips
<Breadcrumb
  items={[
    { label: 'Executive', href: '/executive', icon: <LayoutDashboard /> },
    { label: 'Pipeline', href: '/executive/pipeline', tooltip: 'Live tender pipeline' },
    { label: 'Agency View', current: true }
  ]}
  maxItems={4}
/>

// Custom separator
<Breadcrumb
  items={[...]}
  separator={<span className="mx-2 text-muted">/</span>}
/>

// With custom render
<Breadcrumb
  items={items}
  renderItem={(item, index, isLast) => (
    <span className={cn(
      'flex items-center gap-1',
      isLast ? 'font-medium' : 'text-muted-foreground'
    )}>
      {item.icon}
      {item.label}
    </span>
  )}
/>
```

---

## Mobile Ellipsis Popover

```
┌─────────────────────────────┐
│ Hidden breadcrumbs          │
├─────────────────────────────┤
│ 🏠 Home                     │
│ 📡 Opportunity              │
│ 📄 Tender                   │
│ 🛡 Trust                    │
│ 📚 Knowledge                │
│ 🏢 Enterprise               │
└─────────────────────────────┘
```

---

## Future Extensions

- [ ] Keyboard navigation (Arrow keys)
- [ ] Custom separator component
- [ ] RTL support
- [ ] Dynamic maxItems based on container width
- [ ] Breadcrumb trail from router
- [ ] Analytics integration