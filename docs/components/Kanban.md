# Kanban Component Contract

**Package**: `widgets/boards`  
**Type**: Board Component  
**Stability**: Stable  

---

## Purpose

Drag-and-drop Kanban board for workflow management. Used for tender pipeline, document approval, and agent task tracking.

---

## Props

```typescript
interface KanbanProps {
  /** Columns */
  columns: KanbanColumn[];
  /** Drag end handler */
  onDragEnd: (result: DragResult) => void;
  /** Column add handler */
  onAddColumn?: () => void;
  /** Card click handler */
  onCardClick?: (card: KanbanCard, columnId: string) => void;
  /** Card context menu */
  onCardContextMenu?: (event: React.MouseEvent, card: KanbanCard, columnId: string) => void;
  /** Custom className */
  className?: string;
}

interface KanbanColumn {
  id: string;
  title: string;
  cards: KanbanCard[];
  /** Max cards before warning */
  maxCards?: number;
  /** Color accent */
  color?: string;
  /** Icon */
  icon?: React.ReactNode;
  /** Custom header render */
  renderHeader?: (column: KanbanColumn) => React.ReactNode;
}

interface KanbanCard {
  id: string;
  title: string;
  description?: string;
  assignee?: { name: string; avatar?: string };
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  tags?: string[];
  dueDate?: Date;
  metadata?: Record<string, any>;
  /** Custom render */
  render?: (card: KanbanCard) => React.ReactNode;
}

interface DragResult {
  draggableId: string;
  type: string;
  source: { droppableId: string; index: number };
  destination?: { droppableId: string; index: number };
  reason: 'DROP' | 'CANCEL';
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `columnHeader` | No | Custom column header |
| `card` | No | Custom card rendering |
| `addCard` | No | Add card button |
| `columnActions` | No | Column menu |

---

## State

| State | Visual |
|-------|--------|
| `idle` | Normal columns |
| `dragging` | Card lifted, placeholder |
| `drag-over` | Column highlight |
| `loading` | Skeleton cards |

---

## Accessibility

- **Role**: `region` with `aria-label="Kanban board"`
- **Columns**: `role="list"` with `aria-label`
- **Cards**: `role="listitem"` with `aria-grabbed`
- **Drag**: `aria-describedby` for instructions
- **Keyboard**: Full keyboard drag-and-drop support

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate columns/cards |
| `Enter` / `Space` | Pick up card |
| `Arrow Keys` | Move card (when grabbed) |
| `Escape` | Cancel drag |
| `Enter` (on column) | Focus first card |
| `Home` / `End` | First/Last card |

---

## Drag & Drop

```tsx
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';

<DragDropContext onDragEnd={handleDragEnd}>
  <Flex gap={4} overflowX="auto" className="kanban-board">
    {columns.map(column => (
      <Droppable key={column.id} droppableId={column.id}>
        {(provided, snapshot) => (
          <Column
            ref={provided.innerRef}
            {...provided.droppableProps}
            column={column}
            isDraggingOver={snapshot.isDraggingOver}
          />
        )}
      </Droppable>
    ))}
</DragDropContext>
```

---

## Usage Examples

```tsx
// Tender pipeline
<Kanban
  columns={[
    { id: 'discovery', title: 'Discovery', cards: discoveryCards, color: '#3B82F6', maxCards: 20 },
    { id: 'qualification', title: 'Qualification', cards: qualCards, color: '#F59E0B', maxCards: 15 },
    { id: 'proposal', title: 'Proposal Prep', cards: proposalCards, color: '#8B5CF6', maxCards: 10 },
    { id: 'submitted', title: 'Submitted', cards: submittedCards, color: '#22C55E' },
    { id: 'awarded', title: 'Awarded', cards: awardedCards, color: '#10B981' },
    { id: 'lost', title: 'Lost', cards: lostCards, color: '#EF4444' }
  ]}
  onDragEnd={handlePipelineDragEnd}
  onCardClick={(card, columnId) => openTenderDetail(card.id)}
/>

// Agent task board
<Kanban
  columns={[
    { id: 'backlog', title: 'Backlog', cards: backlogTasks, color: '#6B7280' },
    { id: 'ready', title: 'Ready', cards: readyTasks, color: '#3B82F6' },
    { id: 'running', title: 'Running', cards: runningTasks, color: '#F59E0B', maxCards: 5 },
    { id: 'completed', title: 'Completed', cards: completedTasks, color: '#22C55E' },
    { id: 'failed', title: 'Failed', cards: failedTasks, color: '#EF4444' }
  ]}
  onDragEnd={handleTaskDragEnd}
  onCardClick={(task) => openAgentLog(task.id)}
/>

// Document approval
<Kanban
  columns={[
    { id: 'draft', title: 'Draft', cards: draftDocs, color: '#6B7280' },
    { id: 'review', title: 'Under Review', cards: reviewDocs, color: '#F59E0B' },
    { id: 'approved', title: 'Approved', cards: approvedDocs, color: '#22C55E' },
    { id: 'rejected', title: 'Rejected', cards: rejectedDocs, color: '#EF4444' }
  ]}
  onDragEnd={handleDocDragEnd}
  onCardClick={(doc) => openDocument(doc.id)}
/>

// Card with metadata
const card = {
  id: 'tender-1298004',
  title: 'Bridge Construction - Chattogram',
  description: '2-lane bridge over Karnaphuli River',
  assignee: { name: 'Rahim Uddin', avatar: '/avatars/rahim.jpg' },
  priority: 'high',
  tags: ['BWDB', 'Zone B', 'Bridge'],
  dueDate: new Date('2026-01-15'),
  render: (card) => (
    <Card className="kanban-card">
      <Flex justify="between" className="mb-2">
        <Badge variant={priorityColor(card.priority)}>{card.priority}</Badge>
        <Text size="xs" className="text-muted">{formatDate(card.dueDate)}</Text>
      </Flex>
      <Text weight="medium" className="mb-1">{card.title}</Text>
      <Text size="sm" className="text-muted line-clamp-2">{card.description}</Text>
      <Flex align="center" gap={2} className="mt-3 pt-2 border-t">
        <Avatar src={card.assignee?.avatar} fallback={card.assignee?.name[0]} size="xs" />
        <Text size="xs">{card.assignee?.name}</Text>
        <Flex gap={1} className="ml-auto">
          {card.tags.map(t => <Badge key={t} variant="outline" size="xs">{t}</Badge>)}
        </Flex>
      </Flex>
    </Card>
  )
};
```

---

## Drag Result Handling

```tsx
const handleDragEnd = (result: DragResult) => {
  if (!result.destination) return;
  
  if (
    result.destination.droppableId === result.source.droppableId &&
    result.destination.index === result.source.index
  ) return;

  // Move card
  const sourceColumn = columns.find(c => c.id === result.source.droppableId);
  const destColumn = columns.find(c => c.id === result.destination.droppableId);
  
  const card = sourceColumn.cards[result.source.index];
  
  // Remove from source
  sourceColumn.cards.splice(result.source.index, 1);
  
  // Add to destination
  destColumn.cards.splice(result.destination.index, 0, card);
  
  // Check max cards warning
  if (destColumn.maxCards && destColumn.cards.length > destColumn.maxCards) {
    toast.warning(`${destColumn.title} exceeds recommended limit`);
  }
  
  // Persist
  saveColumnOrder(columns);
  
  // Analytics
  track('kanban_move', {
    card_id: card.id,
    from_column: result.source.droppableId,
    to_column: result.destination.droppableId
  });
};
```

---

## Future Extensions

- [ ] Swimlanes (group by assignee/priority)
- [ ] WIP limits enforcement
- [ ] Card dependencies (blockers)
- [ ] Time in column tracking
- [ ] Auto-transition rules
- [ ] Board templates
- [ ] Export/import board state
- [ ] Real-time collaboration