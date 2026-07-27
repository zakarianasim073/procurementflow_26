# AvatarGroup Component Contract

**Package**: `shared/ui`  
**Type**: Display Component  
**Stability**: Stable  

---

## Purpose

Stacked avatar group for displaying multiple users/agents with overflow count. Used in assignee lists, collaborator lists, and agent teams.

---

## Props

```typescript
interface AvatarGroupProps {
  /** Avatars to display */
  avatars: AvatarGroupItem[];
  /** Max visible before overflow */
  max?: number; // default: 5
  /** Size variant */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** Shape */
  shape?: 'circle' | 'square';
  /** Overlap direction */
  overlapDirection?: 'left' | 'right'; // default: 'left'
  /** Show overflow count */
  showCount?: boolean; // default: true
  /** Custom overflow render */
  renderOverflow?: (count: number) => React.ReactNode;
  /** Custom className */
  className?: string;
}

interface AvatarGroupItem {
  src?: string;
  name?: string;
  initials?: string;
  alt?: string;
  status?: 'online' | 'offline' | 'busy' | 'away' | 'running' | 'error';
  href?: string;
  onClick?: () => void;
  tooltip?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `avatar` | No | Custom avatar rendering |
| `overflow` | No | Custom overflow badge |

---

## State

| State | Visual |
|-------|--------|
| `default` | Overlapping avatars + overflow badge |
| `expanded` | Hover/focus shows all avatars in tooltip |
| `compact` | `max=3` for tight spaces |

---

## Accessibility

- **Role**: `group` with `aria-label="[count] collaborators"`
- **Avatars**: Individual `img` or `role="img"` with alt
- **Overflow**: `aria-label="[count] more collaborators"`
- **Keyboard**: Tab to group, arrow keys navigate

---

## Usage Examples

```tsx
// Basic collaborator list
<AvatarGroup
  avatars={[
    { src: '/avatars/user1.jpg', name: 'Alice Rahman', status: 'online' },
    { src: '/avatars/user2.jpg', name: 'Bob Ahmed', status: 'busy' },
    { src: '/avatars/user3.jpg', name: 'Carol Islam', status: 'away' },
    { src: '/avatars/user4.jpg', name: 'David Khan', status: 'offline' },
  ]}
/>

// With overflow
<AvatarGroup
  max={3}
  avatars={teamMembers}
  renderOverflow={(count) => <Badge variant="outline">+{count}</Badge>}
/>

// Agent team
<AvatarGroup
  avatars={[
    { name: 'BOQ Agent', initials: 'BA', status: 'running', shape: 'square' },
    { name: 'Document AI', initials: 'DA', status: 'idle', shape: 'square' },
    { name: 'Rate Analysis', initials: 'RA', status: 'success', shape: 'square' },
    { name: 'Compliance', initials: 'CC', status: 'error', shape: 'square' },
  ]}
  shape="square"
  size="md"
/>

// Compact for cards
<AvatarGroup
  size="xs"
  max={2}
  avatars={assignees}
  className="ml-auto"
/>

// With tooltips
<AvatarGroup
  avatars={[
    { name: 'Alice', src: '/alice.jpg', tooltip: 'Alice Rahman - Lead Estimator' },
    { name: 'Bob', src: '/bob.jpg', tooltip: 'Bob Ahmed - Sr. Engineer' },
  ]}
/>

// Clickable avatars
<AvatarGroup
  avatars={[
    { name: 'Alice', src: '/alice.jpg', href: '/user/alice' },
    { name: 'Bob', src: '/bob.jpg', onClick: () => openProfile('bob') },
  ]}
/)
```

---

## Sizes

| Size | Diameter | Overlap | Font |
|------|----------|---------|------|
| `xs` | 24px | 8px | `text-xs` |
| `sm` | 32px | 10px | `text-sm` |
| `md` | 40px | 12px | `text-sm` |
| `lg` | 56px | 16px | `text-base` |

---

## Future Extensions

- [ ] Drag-to-reorder
- [ ] Keyboard navigation (arrow keys)
- [ ] Popover on hover with details
- [ ] Group by team/project
- [ ] Virtualized for large groups