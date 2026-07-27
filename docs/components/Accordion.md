# Accordion Component Contract

**Package**: `shared/ui`  
**Type**: Disclosure Component  
**Stability**: Stable  

---

## Purpose

Collapsible content sections for FAQs, settings groups, and progressive disclosure. Supports single/multiple open, animations, and keyboard navigation.

---

## Props

```typescript
interface AccordionProps {
  /** Items */
  items: AccordionItem[];
  /** Allow multiple open */
  multiple?: boolean; // default: false
  /** Default open keys */
  defaultOpen?: string[];
  /** Controlled open keys */
  open?: string[];
  onChange?: (keys: string[]) => void;
  /** Allow toggle (click header) */
  allowToggle?: boolean; // default: true
  /** Custom className */
  className?: string;
}

interface AccordionItem {
  key: string;
  header: React.ReactNode;
  content: React.ReactNode;
  disabled?: boolean;
  icon?: React.ReactNode;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom header rendering |
| `content` | No | Custom content rendering |
| `icon` | No | Custom expand/collapse icon |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | Default | Header only, chevron down |
| `open` | Click/header | Content visible, chevron up |
| `disabled` | `disabled=true` | Muted, not clickable |
| `animating` | Transition | Height transition |

---

## Accessibility

- **Role**: `region` with `aria-labelledby`
- **Header**: `button` with `aria-expanded`, `aria-controls`
- **Content**: `role="region"`, `aria-hidden` when closed
- **Keyboard**: Full navigation

---

## Keyboard

| Key | Action |
|-----|--------|
| `Enter` / `Space` | Toggle |
| `Arrow Down` | Next header |
| `Arrow Up` | Previous header |
| `Home` | First header |
| `End` | Last header |
| `Ctrl+Arrow Down` | Open all (multiple) |
| `Ctrl+Arrow Up` | Close all (multiple) |

---

## Usage Examples

```tsx
// Basic
<Accordion
  items={[
    { key: '1', header: 'What is BOQ?', content: <p>Bill of Quantities...</p> },
    { key: '2', header: 'How to compare?', content: <p>Upload BOQ and select SOR...</p> },
  ]}
/>

// Multiple open
<Accordion
  multiple
  defaultOpen={['1', '3']}
  items={faqItems}
/>

// With custom header
<Accordion
  items={[
    {
      key: 'settings',
      header: (
        <Flex align="center" justify="between">
          <Text weight="medium">Notifications</Text>
          <Badge variant="success">3 new</Badge>
        </Flex>
      ),
      content: <NotificationSettings />
    }
  ]}
  multiple
/>

// Controlled
<Accordion
  open={openKeys}
  onChange={setOpenKeys}
  items={items}
/>

// Disabled item
<Accordion
  items={[
    { key: '1', header: 'Available', content: <p>Content</p> },
    { key: '2', header: 'Disabled', content: <p>Not available</p>, disabled: true },
  ]}
/>
```

---

## Future Extensions

- [ ] Lazy content loading
- [ ] Nested accordions
- [ ] Search within accordion
- [ ] Stepper integration