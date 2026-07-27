# Sidebar Component Contract

**Module:** `shared/ui/Sidebar`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Persistent navigation sidebar that provides workspace-aware navigation across all 6 ProcureFlow workspaces (Dashboard, Discovery, Acquisition, Intelligence, Knowledge, Settings).

## Props
```typescript
interface SidebarProps {
  collapsed?: boolean;
  onToggle?: (collapsed: boolean) => void;
  workspace: WorkspaceId;
  sections: SidebarSection[];
  activeRoute: string;
  onNavigate: (route: string) => void;
  user?: User | null;
  onLogout?: () => void;
  className?: string;
  testId?: string;
}

interface SidebarSection {
  id: string;
  label: string;
  items: SidebarItem[];
  badge?: number;
}

interface SidebarItem {
  id: string;
  label: string;
  icon: ReactNode;
  route: string;
  badge?: number;
  disabled?: boolean;
  tooltip?: string;
}

type WorkspaceId = 'dashboard' | 'discovery' | 'acquisition' | 'intelligence' | 'knowledge' | 'settings';
```

## Slots
- `logo` — Workspace logo/branding
- `header` — Workspace title + collapse toggle
- `content` — Scrollable navigation sections
- `footer` — User profile, settings, logout

## State
```typescript
interface SidebarState {
  isCollapsed: boolean;
  expandedSections: Set<string>;
  hoverItem: string | null;
}
```

## Accessibility
- **ARIA:** `role="navigation"`, `aria-label="Main navigation"`, `aria-current="page"` on active
- **Keyboard:** Arrow keys navigate items, Enter/Space activate, Escape collapses
- **Focus:** Roving tabindex within sections, visible focus ring

## Loading
- Skeleton sidebar with matching item count during initial load

## Errors
- N/A — navigation component

## Keyboard
| Key | Action |
|-----|--------|
| ArrowDown | Next item |
| ArrowUp | Previous item |
| ArrowRight | Expand section |
| ArrowLeft | Collapse section |
| Enter | Navigate to item |
| Home | First item |
| End | Last item |

## Mobile
- Hidden by default; toggle via hamburger
- Full-screen overlay with backdrop
- Swipe left to close

## Permissions
- Items filtered by user role/permissions
- Disabled items for unauthorized routes

## Telemetry
- `sidebar.navigate` — Item clicked (item id, route)
- `sidebar.toggle` — Collapsed/expanded

## React Query
- `useWorkspaces()` for workspace data
- `useUserInfo()` for user profile

## Dependencies
- `shared/navigation/workspaces.ts` — Workspace definitions
- `shared/ui/Badge` — Notification counts
- `shared/ui/Tooltip` — Collapsed mode tooltips
- `shared/ui/Avatar` — User profile image

## Future Extensions
- Drag-to-reorder sections
- Customizable quick actions
- Workspace-specific color themes
- Keyboard shortcut indicators
