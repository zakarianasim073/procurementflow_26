# Tabs Component Contract

**Package**: `shared/ui`  
**Type**: Navigation Component  
**Stability**: Stable  

---

## Purpose

Tabbed interface for organizing content into separate panes. Supports horizontal, vertical, and card variants with keyboard navigation and lazy loading.

---

## Props

```typescript
interface TabsProps {
  /** Tab items */
  items: TabItem[];
  /** Active tab key */
  activeKey: string;
  /** Change handler */
  onChange: (key: string) => void;
  /** Variant */
  variant?: 'line' | 'enclosed' | 'soft' | 'card';
  /** Orientation */
  orientation?: 'horizontal' | 'vertical';
  /** Lazy load panels */
  lazy?: boolean;
  /** Custom className */
  className?: string;
}

interface TabItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  badge?: string | number;
  content: React.ReactNode;
}
```

---

## Variants

| Variant | Visual | Use Case |
|---------|--------|----------|
| `line` | Bottom border line | Default, content sections |
| `enclosed` | Full border, rounded | Settings, forms |
| `soft` | Background highlight | Toolbars, filters |
| `card` | Card per panel | Wizards, dashboards |

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `tabList` | No | Custom tab list |
| `tabPanel` | No | Custom panel wrapper |
| `indicator` | No | Custom active indicator |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `active` | `activeKey` match | Highlighted, panel visible |
| `inactive` | Default | Muted, panel hidden |
| `disabled` | `disabled=true` | Muted, not clickable |
| `focus` | Keyboard | Ring outline |
| `loading` | Async panel | Skeleton |

---

## Accessibility

- **Role**: `tablist` / `tab` / `tabpanel`
- **ARIA**: `aria-selected`, `aria-controls`, `aria-labelledby`
- **Keyboard**: Full roving tabindex pattern
- **Screen Reader**: Announces tab changes

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Left/Right` | Previous/Next tab (horizontal) |
| `Arrow Up/Down` | Previous/Next tab (vertical) |
| `Home` / `End` | First/Last tab |
| `Enter` / `Space` | Activate tab |
| `Tab` | Enter panel |
| `Ctrl+Tab` | Next tab (global) |

---

## Loading

- **Panel**: Skeleton on first load if `lazy=true`
- **Switch**: Instant (client-side)

---

## Errors

Not applicable

---

## Mobile

- **Horizontal**: Scrollable tabs, swipe to switch
- **Vertical**: Stacked, full width
- **Card**: Stacked cards

---

## Permissions

| Role | Access |
|------|--------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `tab_switch` | `from`, `to`, `variant` |

---

## React Query

```typescript
// Lazy panels with queries
<Tabs
  lazy
  items={[
    { key: 'overview', label: 'Overview', content: <OverviewPanel /> },
    { key: 'analytics', label: 'Analytics', content: <AnalyticsPanel /> }
  ]}
/>
```

---

## Dependencies

- `lucide-react`: `ChevronRight`, `ChevronDown`

---

## Usage Examples

```tsx
// Basic
<Tabs
  activeKey={activeTab}
  onChange={setActiveTab}
  items={[
    { key: 'boq', label: 'BOQ', content: <BoqTable data={data} /> },
    { key: 'pricing', label: 'Pricing', content: <PricingPanel /> },
    { key: 'compliance', label: 'Compliance', content: <ComplianceChecklist /> }
  ]}
/>

// Vertical
<Tabs
  orientation="vertical"
  variant="enclosed"
  activeKey={section}
  onChange={setSection}
  items={[
    { key: 'info', label: 'Tender Info', content: <TenderInfo /> },
    { key: 'boq', label: 'BOQ Items', content: <BoqList /> },
    { key: 'docs', label: 'Documents', content: <DocumentViewer /> }
  ]}
/>

// With badges
<Tabs
  items={[
    { key: 'all', label: 'All', badge: 1247 },
    { key: 'active', label: 'Active', badge: 89 },
    { key: 'pending', label: 'Pending', badge: 23 }
  ]}
/>

// Card variant (wizard)
<Tabs
  variant="card"
  orientation="vertical"
  activeKey={step}
  onChange={setStep}
  items={[
    { key: '1', label: 'Step 1: Details', content: <Step1Form /> },
    { key: '2', label: 'Step 2: BOQ', content: <Step2Form /> },
    { key: '3', label: 'Step 3: Review', content: <Step3Form /> }
  ]}
/>
```

---

## Future Extensions

- [ ] Animated transitions (slide, fade)
- [ ] Draggable reorder
- [ ] Closeable tabs
- [ ] New tab button
- [ ] Tab overflow menu
- [ ] Persisted active tab