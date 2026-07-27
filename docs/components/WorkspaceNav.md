# WorkspaceNav Component Contract

**Package**: `layouts/navigation`  
**Type**: Navigation Component  
**Stability**: Stable  

---

## Purpose

Main navigation component providing workspace switching and section navigation. Implements responsive patterns: sidebar (≥1024px), icon rail (768-1024px), drawer (<768px). Core to all workspace screens.

---

## Props

```typescript
interface WorkspaceNavProps {
  /** Active workspace ID */
  activeWorkspace: WorkspaceId;
  /** Workspace change handler */
  onWorkspaceChange: (workspaceId: WorkspaceId) => void;
  /** Active section within workspace */
  activeSection?: string;
  /** Section change handler */
  onSectionChange?: (sectionId: string) => void;
  /** Collapsed state (icon rail mode) */
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
  /** Drawer open state (mobile) */
  drawerOpen?: boolean;
  onDrawerOpenChange?: (open: boolean) => void;
  /** Custom className */
  className?: string;
}

type WorkspaceId = 
  | 'executive' 
  | 'opportunity' 
  | 'tender' 
  | 'trust' 
  | 'knowledge' 
  | 'enterprise';
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `brand` | No | Custom logo/brand |
| `user` | No | User avatar/menu |
| `footer` | No | Version, help links |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `sidebar` | ≥1024px, not collapsed | Full labels, 224px width |
| `rail` | 768-1024px or collapsed | Icons only, 64px width |
| `drawer` | <768px, drawerOpen | Overlay, 280px width |
| `hover` | Mouse enter rail | Tooltip labels |
| `focus` | Keyboard navigation | Focus ring |

---

## Accessibility

- **Role**: `navigation` with `aria-label="Main navigation"`
- **Workspace Switcher**: `radiogroup` with `aria-label="Workspace"`
- **Sections**: `menu` with `aria-label="[Workspace] sections"`
- **Roving Tabindex**: Arrow keys cycle within group
- **Focus Management**: Restores focus on drawer close
- **ARIA**: `aria-current="page"` on active items

---

## Loading

Not applicable (static navigation)

---

## Errors

Not applicable

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Enter/Exit navigation |
| `Arrow Up/Down` | Navigate sections |
| `Arrow Left/Right` | Switch workspaces (in switcher) |
| `Enter` / `Space` | Activate item |
| `Escape` | Close drawer / Collapse rail |
| `Ctrl+B` | Toggle collapse |
| `Home` / `End` | First/Last item |

---

## Mobile

- **< 768px**: Drawer overlay with backdrop blur
- **Swipe**: Edge swipe opens drawer
- **Backdrop**: Click closes drawer
- **Safe Area**: Inset for notches
- **Sections**: Collapsible accordion

---

## Permissions

| Role | Workspace Access |
|------|------------------|
| `viewer` | executive, opportunity, trust |
| `estimator` | + tender |
| `compliance` | + tender, knowledge |
| `admin` | + enterprise |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `nav_workspace_switch` | `from`, `to` |
| `nav_section_click` | `workspace`, `section` |
| `nav_collapse_toggle` | `collapsed` |
| `nav_drawer_toggle` | `open` |

---

## React Query

```typescript
// Permissions from auth context
const { data: permissions } = useQuery({
  queryKey: authKeys.permissions(),
  select: (data) => data.workspaces
});
```

---

## Dependencies

- `WorkspaceSwitcher` (workspace tabs)
- `WorkspaceSectionList` (section menu)
- `Tooltip` (rail hover labels)
- `Drawer` (mobile overlay)
- `lucide-react`: `LayoutDashboard`, `Radar`, `FileText`, `ShieldCheck`, `BookOpen`, `Building2`, `ChevronLeft`, `ChevronRight`, `Menu`, `X`, `Sun`, `Moon`, `User`, `Settings`, `LogOut`

---

## Workspace Configuration

```typescript
const WORKSPACES: Workspace[] = [
  {
    id: 'executive',
    label: 'Executive',
    icon: LayoutDashboard,
    path: '/executive',
    sections: [
      { id: 'overview', label: 'Overview', path: '/executive' },
      { id: 'pipeline', label: 'Pipeline', path: '/executive/pipeline' }
    ]
  },
  {
    id: 'opportunity',
    label: 'Opportunity',
    icon: Radar,
    path: '/opportunity',
    sections: [
      { id: 'discovery', label: 'Discovery', path: '/opportunity/discovery' },
      { id: 'qualification', label: 'Qualification', path: '/opportunity/qualification' },
      { id: 'monitoring', label: 'Monitoring', path: '/opportunity/monitoring' }
    ]
  },
  // ... tender, trust, knowledge, enterprise
];
```

---

## Layout Breakpoints

| Breakpoint | Mode | Width | Behavior |
|------------|------|-------|----------|
| `< 768px` | Drawer | 280px | Overlay, swipe to open |
| `768-1023px` | Rail | 64px | Icons only, hover tooltip |
| `≥ 1024px` | Sidebar | 224px | Full labels, collapsible |

---

## Future Extensions

- [ ] Keyboard shortcut hints on hover
- [ ] Recent sections quick access
- [ ] Customizable workspace order
- [ ] Notification badges on sections
- [ ] Command palette integration (Ctrl+K)