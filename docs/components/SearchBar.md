# SearchBar Component Contract

**Package**: `widgets/search`  
**Type**: Search Component  
**Stability**: Stable  

---

## Purpose

Global search input with autocomplete, recent searches, suggested filters, and keyboard shortcuts. Used across all workspaces for universal search.

---

## Props

```typescript
interface SearchBarProps {
  /** Current search value */
  value: string;
  /** Change handler */
  onChange: (value: string) => void;
  /** Submit handler */
  onSubmit: (value: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Recent searches */
  recentSearches?: string[];
  /** Suggested filters */
  suggestedFilters?: SearchFilter[];
  /** Loading state */
  loading?: boolean;
  /** Debounce (ms) */
  debounce?: number; // default: 300
  /** Clearable */
  clearable?: boolean; // default: true
  /** Auto-focus */
  autoFocus?: boolean;
  /** Custom className */
  className?: string;
}

interface SearchFilter {
  key: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
  apply: (value: string) => void;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `prefix` | No | Leading icon/action |
| `suffix` | No | Trailing action (filter, voice) |
| `suggestions` | No | Custom suggestion rendering |
| `recent` | No | Custom recent search item |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Empty, placeholder |
| `focused` | Click/Tab | Ring, expanded |
| `typing` | Input | Debounced |
| `loading` | `loading=true` | Spinner in suffix |
| `suggestions` | Has suggestions | Dropdown open |
| `recent` | Focus + empty | Recent list |
| `error` | API error | Red border |

---

## Accessibility

- **Role**: `combobox` with `aria-autocomplete="list"`
- **ARIA**: `aria-expanded`, `aria-controls`, `aria-activedescendant`
- **Keyboard**: Full combobox pattern
- **Screen Reader**: Announces result count

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus |
| `Enter` | Submit / Select highlighted |
| `Escape` | Close suggestions / Clear |
| `Arrow Down/Up` | Navigate suggestions |
| `Arrow Right` | Accept completion |
| `Ctrl+K` / `Cmd+K` | Focus (global) |
| `Backspace` | Clear (when empty) |

---

## Usage Examples

```tsx
// Basic
<SearchBar
  value={query}
  onChange={setQuery}
  onSubmit={handleSearch}
  placeholder="Search tenders, contractors, awards..."
  recentSearches={recent}
  suggestedFilters={[
    { key: 'agency', label: 'Agency', icon: <Building /> },
    { key: 'zone', label: 'Zone', icon: <MapPin /> },
    { key: 'value', label: 'Value Range', icon: <DollarSign /> }
  ]}
/>

// With global shortcut
useHotkeys('mod+k', () => searchRef.current?.focus(), { preventDefault: true });

// Custom suggestions={
  results.map(r => (
    <SearchSuggestion
      key={r.id}
      item={r}
      highlighted={r.id === highlightedId}
      onSelect={() => handleSelect(r)}
    />
  ))
/>
```

---

## Suggestion Item

```tsx
interface SearchSuggestionProps {
  item: {
    id: string;
    type: 'tender' | 'contractor' | 'award' | 'document';
    title: string;
    subtitle?: string;
    meta?: string;
    icon?: React.ReactNode;
  };
  highlighted: boolean;
  onSelect: () => void;
}
```

---

## Filter Suggestions

```tsx
suggestedFilters={[
  { key: 'agency', label: 'Agency', icon: <Building />, apply: (v) => setFilter('agency', v) },
  { key: 'zone', label: 'Zone', icon: <MapPin />, apply: (v) => setFilter('zone', v) },
  { key: 'value', label: 'Value', icon: <DollarSign />, apply: (v) => setFilter('value', v) },
  { key: 'date', label: 'Date Range', icon: <Calendar />, apply: (v) => setFilter('date', v) },
  { key: 'status', label: 'Status', icon: <Flag />, apply: (v) => setFilter('status', v) }
]}
```

---

## Recent Searches (localStorage)

```tsx
const [recent, setRecent] = useState(() => 
  JSON.parse(localStorage.getItem('recent_searches') || '[]')
);

const handleSubmit = (query: string) => {
  setRecent(prev => {
    const filtered = prev.filter(q => q !== query);
    const updated = [query, ...filtered].slice(0, 10);
    localStorage.setItem('recent_searches', JSON.stringify(updated));
    return updated;
  });
  handleSearch(query);
};
```

---

## Future Extensions

- [ ] Semantic search (vector)
- [ ] Search analytics dashboard
- [ ] Saved searches
- [ ] Search history sync
- [ ] Voice search (Web Speech)
- [ ] Image search
- [ ] Search within results