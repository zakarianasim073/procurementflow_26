# Avatar Component Contract

**Package**: `shared/ui`  
**Type**: Display Component  
**Stability**: Stable  

---

## Purpose

User/agent avatar with image, fallback initials, status indicator, and size variants. Used in headers, activity feeds, assignee lists, and agent cards.

---

## Props

```typescript
interface AvatarProps {
  /** Image source */
  src?: string;
  /** Fallback initials (auto-generated from name if not provided) */
  initials?: string;
  /** Display name (for initials generation) */
  name?: string;
  /** Alt text */
  alt?: string;
  /** Size variant */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** Shape */
  shape?: 'circle' | 'square';
  /** Status indicator */
  status?: 'online' | 'offline' | 'busy' | 'away' | 'running' | 'error';
  /** Status position */
  statusPosition?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  /** Border */
  bordered?: boolean;
  /** Click handler */
  onClick?: () => void;
  /** Custom className */
  className?: string;
}
```

---

## Sizes

| Size | Dimensions | Font | Status Size |
|------|------------|------|-------------|
| `xs` | 24×24px | `text-xs` | 8px |
| `sm` | 32×32px | `text-sm` | 10px |
| `md` | 40×40px | `text-sm` | 12px |
| `lg` | 56×56px | `text-base` | 14px |
| `xl` | 80×80px | `text-lg` | 16px |

---

## Status Colors

| Status | Color | Use Case |
|--------|-------|----------|
| `online` | Green | Active user |
| `offline` | Gray | Inactive |
| `busy` | Red | Do not disturb |
| `away` | Amber | Away/idle |
| `running` | Blue | Agent executing |
| `error` | Red | Agent failed |

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| — | — | Self-contained |

---

## State

| State | Visual |
|-------|--------|
| `image` | `src` loaded |
| `initials` | Generated from name |
| `fallback` | Generic icon |
| `loading` | Skeleton |
| `error` | Fallback to initials |

---

## Accessibility

- **Role**: `img` (image) / `none` (initials)
- **Alt**: `alt` prop or `name + " avatar"`
- **Status**: `aria-label="Status: [status]"`
- **Clickable**: `role="button"` if `onClick`

---

## Loading

- **Skeleton**: Gray circle with pulse
- **Image Error**: Auto-fallback to initials

---

## Errors

- **Image Failed**: Silent fallback to initials
- **No Name/Initials**: Generic user icon

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus (if clickable) |
| `Enter` / `Space` | Click |

---

## Mobile

- **Touch**: 44×44mm minimum
- **Sizes**: Same scale

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `avatar_click` | `user_id`, `source` |

---

## React Query

```typescript
const { data: user } = useQuery({
  queryKey: ['user', userId],
  select: (data) => ({
    src: data.avatar_url,
    name: data.full_name,
    status: data.presence
  })
});
```

---

## Dependencies

- `lucide-react`: `User`, `Bot`, `AlertCircle`, `CheckCircle`, `Clock`, `Zap`

---

## Usage Examples

```tsx
// User avatar with status
<Avatar
  src={user.avatar_url}
  name={user.full_name}
  size="md"
  status="online"
/>

// Agent avatar
<Avatar
  name="BOQ Intelligence Agent"
  size="lg"
  status="running"
  shape="square"
/>

// Fallback initials
<Avatar
  name="Zakaria Nasim"
  size="xl"
  bordered
/>

// Clickable
<Avatar
  src={user.avatar}
  name={user.name}
  onClick={() => openProfile(user.id)}
/>

// Group
<AvatarGroup>
  <Avatar name="User 1" />
  <Avatar name="User 2" />
  <Avatar name="User 3" />
  <Avatar count={5} />
</AvatarGroup>
```

---

## Future Extensions

- [ ] AvatarGroup component (overlapping stack)
- [ ] Badge overlay (notification count)
- [ ] Custom status colors
- [ ] Animated status pulse
- [ ] Image crop/zoom