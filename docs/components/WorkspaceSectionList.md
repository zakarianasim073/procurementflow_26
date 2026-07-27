# WorkspaceSectionList Component Contract

**Package**: `layouts/navigation`  
**Type**: Navigation Component  
**Stability**: Stable  

---

## Purpose

Vertical section list for the active workspace. Displays navigable sections with icons, labels, and optional badges. Supports collapsible groups, permission filtering, and roving tabindex for keyboard navigation.

---

## Props

```typescript
interface WorkspaceSectionListProps {
  /** Workspace ID */
  workspaceId: WorkspaceId;
  /** Active section ID */
  activeSection?: string;
  /** Section change handler */
  onSectionChange: (sectionId: string) => void;
  /** Collapsible groups */
  collapsible?: boolean;
  /** Default expanded groups */
  defaultExpanded?: string[];
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
| `section` | No | Custom section rendering |
| `groupHeader` | No | Custom group header |
| `badge` | No | Custom badge (count, status) |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Expanded groups, active highlighted |
| `collapsed` | Group click | Chevron rotated, sections hidden |
| `active` | Current route | Brand background, white text |
| `disabled` | No permission | Muted, cursor not-allowed |
| `hover` | Mouse enter | Subtle background |
| `focus` | Keyboard | Ring outline |

---

## Accessibility

- **Role**: `navigation` with `aria-label="[Workspace] sections"`
- **Groups**: `role="group"` with `aria-labelledby`
- **Items**: `role="menuitem"` with `aria-current="page"`
- **Roving Tabindex**: Arrow Up/Down navigate, Tab exits
- **Expand/Collapse**: `aria-expanded` on group headers
- **Screen Reader**: Announces "Section [name], [workspace] workspace"

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
| `Arrow Up/Down` | Navigate sections |
| `Arrow Left/Right` | Collapse/expand group |
| `Enter` / `Space` | Activate section / Toggle group |
| `Home` / `End` | First/Last section |
| `Tab` | Exit to next focusable |
| `Escape` | Collapse all groups |

---

## Mobile

- **Drawer Mode**: Full-height scrollable list
- **Groups**: Collapsible by default
- **Touch**: Tap to navigate, long press for context menu
- **Safe Area**: Bottom padding for home indicator

---

## Permissions

| Role | Executive | Opportunity | Tender | Trust | Knowledge | Enterprise |
|------|-----------|-------------|--------|-------|-----------|------------|
| `viewer` | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| `estimator` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `compliance` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `section_navigate` | `workspace`, `section`, `group` |
| `section_group_toggle` | `workspace`, `group`, `expanded` |

---

## React Query

```typescript
const sections = useWorkspaceSections(workspaceId);
// Returns filtered sections based on user permissions
```

---

## Dependencies

- `CollapsibleGroup` (group expand/collapse)
- `SectionItem` (individual section link)
- `Badge` (notification counts)
- `Tooltip` (truncated labels)
- `lucide-react`: Dynamic icons per section

---

## Section Configuration

```typescript
const WORKSPACE_SECTIONS: Record<WorkspaceId, Section[]> = {
  executive: [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard, path: '/executive' },
    { id: 'pipeline', label: 'Pipeline', icon: GitBranch, path: '/executive/pipeline' },
    { id: 'reports', label: 'Reports', icon: FileText, path: '/executive/reports' }
  ],
  opportunity: [
    { id: 'discovery', label: 'Discovery', icon: Search, path: '/opportunity/discovery' },
    { id: 'qualification', label: 'Qualification', icon: CheckSquare, path: '/opportunity/qualification' },
    { id: 'monitoring', label: 'Monitoring', icon: Activity, path: '/opportunity/monitoring' }
  ],
  tender: [
    { id: 'boq', label: 'BOQ & Documents', icon: FileText, path: '/tender/boq' },
    { id: 'pricing', label: 'Pricing', icon: DollarSign, path: '/tender/pricing' },
    { id: 'compliance', label: 'Compliance', icon: ShieldCheck, path: '/tender/compliance' },
    { id: 'competitors', label: 'Competitors', icon: Users, path: '/tender/competitors' },
    { id: 'award', label: 'Award', icon: Trophy, path: '/tender/award' }
  ],
  trust: [
    { id: 'chat', label: 'AI Chat', icon: MessageSquare, path: '/trust/chat' },
    { id: 'agents', label: 'Agent Activity', icon: Bot, path: '/trust/agents' }
  ],
  knowledge: [
    { id: 'market', label: 'Market Research', icon: BarChart, path: '/knowledge/market' },
    { id: 'documents', label: 'Document Tools', icon: FileText, path: '/knowledge/documents' },
    { id: 'analytics', label: 'Analytics', icon: PieChart, path: '/knowledge/analytics' }
  ],
  enterprise: [
    { id: 'clients', label: 'Clients', icon: Users, path: '/enterprise/clients' },
    { id: 'team', label: 'Team', icon: UserPlus, path: '/enterprise/team' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/enterprise/settings' },
    { id: 'roles', label: 'Roles & Permissions', icon: Shield, path: '/enterprise/roles', permission: 'enterprise:admin' }
  ]
};
```

---

## Layout

```
┌─────────────────────────────────┐
│ ▼ EXECUTIVE                    │
│   ┌─────────────────────────┐  │
│   │ 📊 Overview        ▸    │  │
│   │ 🌲 Pipeline        ▸    │  │
│   │ 📄 Reports         ▸    │  │
│   └─────────────────────────┘  │
├─────────────────────────────────┤
│ ▼ OPPORTUNITY                  │
│   ┌─────────────────────────┐  │
│   │ 🔍 Discovery       ▸    │  │
│   │ ✅ Qualification   ▸    │  │
│   │ 📈 Monitoring      ▸    │  │
│   └─────────────────────────┘  │
└─────────────────────────────────┘
```

---

## Future Extensions

- [ ] Drag to reorder sections
- [ ] Pinned/favorite sections
- [ ] Section-level permissions UI
- [ ] Notification badges (count)
- [ ] Search/filter sections
- [ ] Keyboard shortcut hints