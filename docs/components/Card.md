# Card Component Contract

**Package**: `shared/ui`  
**Type**: Layout Component  
**Stability**: Stable  

---

## Purpose

Flexible container for grouping related content with consistent styling, elevation, and interaction patterns.

---

## Props

```typescript
interface CardProps {
  /** Card content */
  children: React.ReactNode;
  /** Header content */
  header?: React.ReactNode;
  /** Footer content */
  footer?: React.ReactNode;
  /** Elevation level */
  elevation?: 'none' | 'sm' | 'md' | 'lg'; // default: 'sm'
  /** Padding */
  padding?: 'none' | 'sm' | 'md' | 'lg'; // default: 'md'
  /** Hover effect */
  hoverable?: boolean;
  /** Click handler (makes card interactive) */
  onClick?: () => void;
  /** Border variant */
  border?: 'default' | 'dashed' | 'none';
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Card header (title, actions) |
| `children` | **Yes** | Main content |
| `footer` | No | Footer actions |

---

## State

| State | Visual |
|-------|--------|
| `default` | Base elevation, border |
| `hover` | Elevated shadow, cursor pointer |
| `active` | Scale 0.98, darker shadow |
| `focus` | Ring outline |
| `loading` | Skeleton overlay |

---

## Accessibility

- **Role**: `article` (default) or `button` (if clickable)
- **Clickable**: `role="button"`, `tabIndex=0`
- **Focus**: Visible ring
- **Screen Reader**: Announces as card region

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus card |
| `Enter` / `Space` | Activate (if clickable) |

---

## Usage Examples

```tsx
// Basic
<Card>
  <Card.Header>
    <Card.Title>Tender 1298004</Card.Title>
    <Card.Subtitle>BWDB • Zone A • ৳45.5M</Card.Subtitle>
  </Card.Header>
  <Card.Content>
    <TenderSummary />
  </Card.Content>
  <Card.Footer>
    <Button variant="ghost">View Details</Button>
    <Button>Compare BOQ</Button>
  </Card.Footer>
</Card>

// Interactive
<Card
  hoverable
  onClick={() => router.push('/tender/1298004')}
  elevation="md"
>
  <CardContent>...</CardContent>
</Card>

// With header actions
<Card
  header={
    <Flex justify="between">
      <Text weight="medium">BOQ Comparison</Text>
      <DropdownMenu>...</DropdownMenu>
    </Flex>
  }
  footer={
    <Flex justify="end" gap={2}>
      <Button variant="secondary">Export</Button>
      <Button>Generate Report</Button>
    </Flex>
  }
>
  <BoqTable data={data} />
</Card>

// Loading state
<Card loading>
  <Skeleton variant="card" />
</Card>

// Grid layout
<Grid cols={{ base: 1, md: 2, lg: 3 }} gap={4}>
  {tenders.map(t => (
    <Card key={t.id} hoverable onClick={() => select(t)}>
      <TenderCardContent tender={t} />
    </Card>
  ))}
</Grid>
```

---

## Sub-components

```tsx
// Card.Header
<Card.Header>
  <Card.Title>Title</Card.Title>
  <Card.Subtitle>Subtitle</Card.Subtitle>
  <Card.Action>Action</Card.Action>
</Card.Header>

// Card.Content
<Card.Content>Content</Card.Content>

// Card.Footer
<Card.Footer>
  <Button>Action</Button>
</Card.Footer>
```

---

## Variants

| Variant | Elevation | Border | Use Case |
|---------|-----------|--------|----------|
| `default` | `sm` | `gray-200` | Standard |
| `elevated` | `md` | `none` | Hover emphasis |
| `outlined` | `none` | `gray-300` | Subtle |
| `filled` | `none` | `none` | `bg-gray-50` |

---

## Future Extensions

- [ ] Expandable/collapsible
- [ ] Drag-and-drop reorder
- [ ] Virtualized list wrapper
- [ ] Masonry layout