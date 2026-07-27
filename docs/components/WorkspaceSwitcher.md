# WorkspaceSwitcher Component Contract

**Package**: `layouts/navigation`  
**Type**: Navigation Component  
**Stability**: Stable  

---

## Purpose

Horizontal tab group for switching between 6 workspaces. Implements roving tabindex pattern for keyboard accessibility. Used in WorkspaceNav header and mobile drawer header.

---

## Props

```typescript
interface WorkspaceSwitcherProps {
  /** Currently active workspace */
  activeWorkspace: WorkspaceId;
  /** Workspace change handler */
  onChange: (workspaceId: WorkspaceId) => void;
  /** Variant */
  variant?: 'tabs' | 'pills' | 'segmented';
  /** Show labels */
  showLabels?: boolean;
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
| `item` | No | Custom workspace button |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Active highlighted, others muted |
| `hover` | Mouse enter | Subtle background |
| `focus` | Keyboard | Ring outline |
| `active` | Current workspace | Brand background, white text |
| `disabled` | No permission | Muted, not clickable |

---

## Accessibility

- **Role**: `radiogroup` with `aria-label="Workspace"`
- **Items**: `role="radio"` with `aria-checked`
- **Roving Tabindex**: Only active item in tab order
- **Arrow Keys**: Left/Right cycle through workspaces
- **Home/End**: First/Last workspace
- **Screen Reader**: Announces workspace name + "selected"

---

## Loading

Not applicable

---

## Errors

Not applicable

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Left/Right` | Previous/Next workspace |
| `Home` | First workspace |
| `End` | Last workspace |
| `Enter` / `Space` | Activate focused workspace |
| `Tab` | Exit to next focusable |

---

## Mobile

- **< 640px**: Horizontal scroll with snap
- **Touch**: Swipe to scroll
- **Labels**: Hidden (icon only), tooltip on long press
- **Active**: Centered on mount

---

## Permissions

| Role | Available Workspaces |
|------|---------------------|
| `viewer` | executive, opportunity, trust |
| `estimator` | + tender |
| `compliance` | + tender, knowledge |
| `admin` | All (including enterprise) |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `workspace_switch` | `from`, `to`, `method` (click, key, swipe) |

---

## React Query

```typescript
const { data: workspaces } = useQuery({
  queryKey: navKeys.workspaces(userRole),
  staleTime: Infinity
});
```

---

## Dependencies

- `Tooltip` (mobile long-press)
- `lucide-react`: `LayoutDashboard`, `Radar`, `FileText`, `ShieldCheck`, `BookOpen`, `Building2`

---

## Workspace Icons & Labels

| ID | Label | Icon | Path |
|----|-------|------|------|
| `executive` | Executive | `LayoutDashboard` | `/executive` |
| `opportunity` | Opportunity | `Radar` | `/opportunity` |
| `tender` | Tender | `FileText` | `/tender` |
| `trust` | Trust Platform | `ShieldCheck` | `/trust` |
| `knowledge` | Knowledge | `BookOpen` | `/knowledge` |
| `enterprise` | Enterprise | `Building2` | `/enterprise` |

---

## Variants

### Tabs (Default)
```
┌─────┬─────────┬──────┬──────┬──────────┬───────────┐
│ 📊  │  📡    │ 📄  │ 🛡  │   📚    │   🏢     │
│Executive Opportunity Tender Trust Knowledge Enterprise│
└─────┴─────────┴──────┴──────┴──────────┴───────────┘
```

### Pills
```
┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌───────┐ ┌────────────┐ ┌────────────┐
│ 📊 Executive │ │ 📡 Opportunity│ │ 📄 Tender│ │🛡 Trust│ │ 📚 Knowledge│ │🏢 Enterprise│
└──────────────┘ └──────────────┘ └──────────┘ └───────┘ └────────────┘ └────────────┘
```

### Segmented (Desktop Only)
```
┌─────────────────────────────────────────────────────────────────────┐
│ ████████████████  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ Executive    Opportunity    Tender    Trust    Knowledge   Enterprise │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Future Extensions

- [ ] Drag to reorder workspaces
- [ ] Keyboard shortcut hints (1-6)
- [ ] Notification badges per workspace
- [ ] Collapsed state (icons only)
- [ ] Custom workspace support