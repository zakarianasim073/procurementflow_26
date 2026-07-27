# TagInput Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Token-based input for multiple values like tags, labels, categories, and entity references. Supports autocomplete, validation, and custom rendering.

---

## Props

```typescript
interface TagInputProps {
  /** Selected tags */
  value: Tag[];
  /** Change handler */
  onChange: (tags: Tag[]) => void;
  /** Suggestions */
  suggestions?: TagSuggestion[];
  /** Async suggestions */
  asyncSuggestions?: (query: string) => Promise<TagSuggestion[]>;
  /** Placeholder */
  placeholder?: string; // default: "Add tags..."
  /** Max tags */
  maxTags?: number;
  /** Allow custom tags (not in suggestions) */
  allowCustom?: boolean;
  /** Custom tag validator */
  validateTag?: (tag: string) => boolean | string;
  /** Disabled */
  disabled?: boolean;
  /** Custom className */
  className?: string;
}

interface Tag {
  id: string;
  label: string;
  color?: string;
  metadata?: Record<string, any>;
}

interface TagSuggestion {
  id: string;
  label: string;
  description?: string;
  color?: string;
  category?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `tag` | No | Custom tag rendering |
| `suggestion` | No | Custom suggestion rendering |
| `input` | No | Custom input rendering |

---

## State

| State | Visual |
|-------|--------|
| `default` | Empty input + tag list |
| `focused` | Ring outline, dropdown open |
| `searching` | Spinner in input |
| `suggestions` | Dropdown with matches |
| `max-reached` | Input disabled, message |
| `error` | Red border, message |

---

## Accessibility

- **Role**: `combobox` with `aria-expanded`
- **Tags**: `role="list"`, each `role="listitem"`
- **Remove**: `button` with `aria-label="Remove [label]"`
- **Keyboard**: Full combobox pattern

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus input |
| `Enter` | Add tag / select suggestion |
| `Backspace` | Remove last tag (when input empty) |
| `Arrow Down/Up` | Navigate suggestions |
| `Escape` | Close suggestions / clear input |
| `Delete` | Remove focused tag |

---

## Usage Examples

```tsx
// Basic tags
<TagInput
  value={selectedAgencies}
  onChange={setSelectedAgencies}
  suggestions={agencySuggestions}
  placeholder="Add agencies..."
  maxTags={5}
/>

// With custom validation
<TagInput
  value={customTags}
  onChange={setCustomTags}
  validateTag={(tag) => {
    if (tag.length < 2) return 'Tag must be at least 2 characters';
    if (tag.length > 30) return 'Tag too long';
    if (!/^[a-zA-Z0-9\s-]+$/.test(tag)) return 'Only letters, numbers, spaces, hyphens';
    return true;
  }}
  allowCustom
  maxTags={10}
  placeholder="Add custom tags..."
/>

// Async suggestions
<TagInput
  value={selectedContractors}
  onChange={setSelectedContractors}
  asyncSuggestions={async (query) => {
    const res = await fetch(`/api/contractors/search?q=${query}`);
    return res.json();
  }}
  placeholder="Search contractors..."
/>

// With custom tag rendering
<TagInput
  value={priorityTags}
  onChange={setPriorityTags}
  suggestions={prioritySuggestions}
  renderTag={(tag, { remove, index }) => (
    <Badge
      variant={tag.color ? 'custom' : 'default'}
      style={{ backgroundColor: tag.color }}
      onRemove={() => remove(index)}
    >
      {tag.label}
    </Badge>
  )}
/>

// Grouped suggestions
<TagInput
  value={filterTags}
  onChange={setFilterTags}
  suggestions={[
    { id: '1', label: 'BWDB', category: 'Agency', color: '#3B82F6' },
    { id: '2', label: 'PWD', category: 'Agency', color: '#8B5CF6' },
    { id: '3', label: 'Zone A', category: 'Zone', color: '#22C55E' },
    { id: '4', label: 'Zone B', category: 'Zone', color: '#F59E0B' },
    { id: '5', label: 'Bridge', category: 'Type', color: '#EF4444' },
    { id: '6', label: 'Road', category: 'Type', color: '#EC4899' },
  ]}
  renderSuggestion={(suggestion) => (
    <Flex align="center" gap={2}>
      <span
        className="w-2 h-2 rounded-full"
        style={{ backgroundColor: suggestion.color }}
      />
      <Text>{suggestion.label}</Text>
      <Text size="xs" className="text-muted">{suggestion.category}</Text>
    </Flex>
  )}
/>
```

---

## Tag Colors

```typescript
const TAG_COLORS = [
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#22C55E', // Green
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#EC4899', // Pink
  '#06B6D4', // Cyan
  '#F97316', // Orange
];
```

---

## Future Extensions

- [ ] Tag categories/groups
- [ ] Drag-drop reorder
- [ ] Tag aliases/synonyms
- [ ] Import/export tags
- [ ] Tag analytics
- [ ] Bulk operations