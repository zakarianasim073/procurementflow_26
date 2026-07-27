# ScreenTemplate Component Contract

**Package**: `layouts`  
**Type**: Layout Component  
**Stability**: Stable  

---

## Purpose

Universal screen template providing consistent 6-slot layout across all screens. Implements responsive grid with sidebar on desktop, stacked on mobile. Core layout primitive for all PFX screens.

---

## Props

```typescript
interface ScreenTemplateProps {
  /** Screen title */
  title: string;
  /** Subtitle/description */
  description?: string;
  /** Breadcrumb items */
  breadcrumbs?: { label: string; href?: string }[];
  /** Slot contents */
  slots: {
    header?: React.ReactNode;
    kpiStrip?: React.ReactNode;
    primary: React.ReactNode;
    aiDock?: React.ReactNode;
    trustPanel?: React.ReactNode;
    activityTimeline?: React.ReactNode;
  };
  /** Slot loading states */
  loading?: Partial<Record<SlotName, boolean>>;
  /** Slot error states */
  errors?: Partial<Record<SlotName, string>>;
  /** Responsive breakpoint */
  breakpoint?: 'sm' | 'md' | 'lg' | 'xl';
  /** Custom className */
  className?: string;
}

type SlotName = 
  | 'header' 
  | 'kpiStrip' 
  | 'primary' 
  | 'aiDock' 
  | 'trustPanel' 
  | 'activityTimeline';
```

---

## Slots

| Slot | Required | Description | Mobile Behavior |
|------|----------|-------------|-----------------|
| `header` | No | Title, breadcrumbs, actions | Collapsed to title only |
| `kpiStrip` | No | Horizontal KPI cards | Horizontal scroll |
| `primary` | **Yes** | Main content area | Full width, stacked |
| `aiDock` | No | AI assistant panel | FAB → bottom sheet |
| `trustPanel` | No | Trust/evidence sidebar | Accordion at bottom |
| `activityTimeline` | No | Activity feed sidebar | Accordion at bottom |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Grid layout per breakpoint |
| `loading` | Slot `loading=true` | Skeleton per slot |
| `error` | Slot `error` prop | Alert in slot |
| `skeleton` | Initial load | Full page skeleton |

---

## Accessibility

- **Landmarks**: `header`, `main`, `aside` (x2), `section`
- **Slot Regions**: `aria-labelledby` referencing slot headers
- **Skip Links**: "Skip to main content" at top
- **Focus Order**: Header → KPI → Primary → AI Dock → Trust → Activity
- **Responsive**: `aria-hidden` for slots not visible at breakpoint

---

## Loading

- **Slot Skeletons**: 
  - Header: Title line + breadcrumb line
  - KPI Strip: 4 card skeletons
  - Primary: Content block skeleton
  - Side slots: Card skeletons
- **Delay**: 100ms per slot

---

## Errors

- **Slot Error**: Inline alert with retry
- **Full Page**: `NotFoundScreen` or `ErrorScreen`

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate slots in order |
| `Shift+Tab` | Reverse navigation |
| `Ctrl+Alt+1-6` | Focus slot (1=header, 2=kpi, 3=primary, etc.) |
| `Escape` | Close mobile sidebars |

---

## Mobile (< 768px)

| Slot | Behavior |
|------|----------|
| `header` | Sticky top, title + breadcrumb collapse |
| `kpiStrip` | Horizontal scroll, snap points |
| `primary` | Full width, stacked |
| `aiDock` | FAB bottom-right → bottom sheet |
| `trustPanel` | Accordion at bottom of primary |
| `activityTimeline` | Accordion below trust |

---

## Desktop (≥ 1024px)

| Slot | Grid Area |
|------|-----------|
| `header` | `1 / 1 / 2 / 3` (span 2 cols) |
| `kpiStrip` | `2 / 1 / 3 / 3` (span 2 cols) |
| `primary` | `3 / 1 / 4 / 2` (left col) |
| `aiDock` | `4 / 2 / 5 / 3` (right, bottom) |
| `trustPanel` | `3 / 2 / 4 / 3` (right, top) |
| `activityTimeline` | `4 / 2 / 5 / 3` (right, middle) |

```
Desktop Grid (lg:):
┌─────────────────────────────────────────────────────────┐
│ Header (span 2)                                         │
├─────────────────────────────────────────────────────────┤
│ KPI Strip (span 2)                                      │
├──────────────────────┬──────────────────────────────────┤
│ Primary Content      │ Trust Panel                       │
│                      ├──────────────────────────────────┤
│                      │ Activity Timeline                 │
│                      ├──────────────────────────────────┤
│                      │ AI Dock (sticky bottom)           │
└──────────────────────┴──────────────────────────────────┘
```

---

## Permissions

| Role | All Slots |
|------|-----------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `screen_template_render` | `screen`, `slots_used`, `breakpoint` |
| `slot_error` | `slot`, `error_type` |

---

## React Query

```typescript
// Each slot typically has its own query
const { data: kpis } = useQuery({ queryKey: dashboardKeys.stats() });
const { data: trust } = useQuery({ queryKey: executiveKeys.report(tenderId) });
const { data: activity } = useQuery({ queryKey: ['activity', tenderId] });
```

---

## Dependencies

- `SlotErrorBoundary` (per-slot error handling)
- `Skeleton` (loading states)
- `ResponsiveGrid` (CSS Grid wrapper)
- `ScrollLock` (mobile sidebar open)
- `lucide-react`: `Loader2`, `AlertTriangle`, `X`

---

## CSS Grid Template

```css
.screen-template {
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: auto auto 1fr auto;
  min-height: 100vh;
}

@media (min-width: 1024px) {
  .screen-template {
    grid-template-columns: 1fr 320px;
    grid-template-rows: 
      auto        /* header */
      auto        /* kpiStrip */
      1fr         /* primary + side */
      auto;       /* aiDock */
    grid-template-areas: 
      "header header"
      "kpiStrip kpiStrip"
      "primary trustPanel"
      "primary activityTimeline"
      "primary aiDock";
  }
}
```

---

## Slot Component Contract

Each slot should implement:

```typescript
interface SlotComponentProps {
  children: React.ReactNode;
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  'aria-labelledby'?: string;
}
```

---

## Future Extensions

- [ ] Slot persistence (localStorage)
- [ ] Slot reordering (drag-drop)
- [ ] Slot visibility toggle
- [ ] Print stylesheet (hide sidebars)
- [ ] RTL support
- [ ] High contrast mode