# Switch Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Toggle switch for boolean settings, feature flags, and on/off states. More intuitive than checkbox for immediate actions.

---

## Props

```typescript
interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Label */
  label?: string;
  /** Description */
  description?: string;
  /** Size */
  size?: 'sm' | 'md' | 'lg';
  /** Disabled */
  disabled?: boolean;
  /** Required */
  required?: boolean;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `label` | No | Custom label |
| `description` | No | Custom description |

---

## State

| State | Visual |
|-------|--------|
| `off` | Thumb left, gray track |
| `on` | Thumb right, brand track |
| `hover` | Track highlight |
| `focus` | Ring on thumb |
| `disabled` | Muted, not clickable |
| `loading` | Spinner in thumb |

---

## Accessibility

- **Role**: `switch` (ARIA)
- **ARIA**: `aria-checked`, `aria-disabled`
- **Label**: `<label htmlFor>`
- **Keyboard**: Space toggles

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus |
| `Space` | Toggle |
| `Enter` | Toggle |

---

## Mobile

- **Touch**: Swipe or tap to toggle
- **Thumb**: 24×24mm minimum
- **Track**: 44×24mm minimum

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `switch_change` | `value` |

---

## Usage Examples

```tsx
// Basic
<Switch
  label="Enable notifications"
  checked={notificationsEnabled}
  onChange={setNotificationsEnabled}
/>

// With description
<Switch
  label="Auto-save drafts"
  description="Automatically save changes every 30 seconds"
  checked={autoSave}
  onChange={setAutoSave}
/>

// In settings row
<Flex align="center" justify="between">
  <Flex flexDir="column" gap={1}>
    <Text weight="medium">Dark mode</Text>
    <Text size="sm" className="text-muted">Uses system preference</Text>
  </Flex>
  <Switch checked={darkMode} onChange={setDarkMode} />
</Flex>

// Loading state
<Switch
  checked={syncEnabled}
  onChange={setSyncEnabled}
  disabled={syncing}
  // Shows spinner in thumb when syncing
/>
```

---

## Future Extensions

- [ ] Custom thumb icons
- [ ] Three-state (on/off/null)
- [ ] Custom colors
- [ ] Animated track gradient