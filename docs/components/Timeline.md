# Timeline Component Contract

**Package**: `widgets/ai`  
**Type**: Data Visualization Component  
**Stability**: Stable  

---

## Purpose

Vertical or horizontal timeline for displaying chronological events, tender milestones, agent execution history, and project progress.

---

## Props

```typescript
interface TimelineProps {
  /** Timeline items */
  items: TimelineItem[];
  /** Orientation */
  orientation?: 'vertical' | 'horizontal';
  /** Layout mode */
  mode?: 'alternating' | 'one-sided';
  /** Show connector line */
  showLine?: boolean; // default: true
  /** Line position */
  linePosition?: 'left' | 'center' | 'right'; // vertical only
  /** Custom className */
  className?: string;
}

interface TimelineItem {
  id: string;
  /** Timestamp */
  timestamp: Date | string;
  /** Title */
  title: string;
  /** Description */
  description?: string;
  /** Event type */
  type?: 'milestone' | 'task' | 'event' | 'decision' | 'document' | 'meeting';
  /** Status */
  status?: 'completed' | 'in-progress' | 'pending' | 'failed' | 'cancelled';
  /** Icon */
  icon?: React.ReactNode;
  /** Color */
  color?: string;
  /** Actor */
  actor?: {
    name: string;
    avatar?: string;
    role?: string;
  };
  /** Related entity */
  entity?: {
    type: 'tender' | 'document' | 'agent' | 'report';
    id: string;
    label: string;
  };
  /** Actions */
  actions?: { label: string; onClick: () => void; variant?: string }[];
  /** Custom content */
  content?: React.ReactNode;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `item` | No | Custom item rendering |
| `dot` | No | Custom dot/marker |
| `connector` | No | Custom line connector |
| `time` | No | Custom time display |

---

## State

| State | Visual |
|-------|--------|
| `completed` | Checkmark, green |
| `in-progress` | Spinner, blue |
| `pending` | Clock, gray |
| `failed` | X-mark, red |
| `current` | Pulse animation, highlight |

---

## Accessibility

- **Role**: `list` with `aria-label="Timeline"`
- **Items**: `role="listitem"` with `aria-label`
- **Time**: `<time>` element with `dateTime`
- **Keyboard**: Arrow keys navigate items

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Up/Down` | Navigate items |
| `Enter` | Open item details |
| `Home/End` | First/Last item |

---

## Usage Examples

```tsx
// Tender milestone timeline
<Timeline
  orientation="vertical"
  mode="alternating"
  items={[
    {
      id: '1',
      timestamp: '2026-01-15T10:00:00Z',
      title: 'Tender Published',
      description: 'NIT published on e-GP portal',
      type: 'milestone',
      status: 'completed',
      icon: <FileText />,
      color: '#22C55E',
      entity: { type: 'tender', id: '1298004', label: 'Tender 1298004' }
    },
    {
      id: '2',
      timestamp: '2026-02-15T17:00:00Z',
      title: 'Bid Submission Deadline',
      description: 'Last date for bid submission',
      type: 'deadline',
      status: 'completed',
      icon: <Calendar />,
      color: '#3B82F6'
    },
    {
      id: '3',
      timestamp: '2026-02-20T10:00:00Z',
      title: 'Bid Opening',
      description: 'Technical and financial bid opening',
      type: 'event',
      status: 'completed',
      icon: <Users />,
      color: '#8B5CF6'
    },
    {
      id: '4',
      timestamp: '2026-03-01T09:00:00Z',
      title: 'Contract Award',
      description: 'Letter of acceptance issued',
      type: 'milestone',
      status: 'in-progress',
      icon: <Award />,
      color: '#F59E0B',
      actor: { name: 'Eng. Rahman', role: 'Procurement Officer' }
    }
  ]}
/>

// Agent execution timeline
<Timeline
  orientation="vertical"
  mode="one-sided"
  items={agentExecutions.map(exec => ({
    id: exec.id,
    timestamp: exec.startedAt,
    title: `${exec.agentName} ${exec.status}`,
    description: exec.summary,
    type: 'agent',
    status: exec.status,
    icon: <Bot />,
    color: exec.status === 'success' ? '#22C55E' : exec.status === 'failed' ? '#EF4444' : '#3B82F6',
    actor: { name: exec.triggeredBy, role: 'System' },
    actions: [{ label: 'View Logs', onClick: () => openAgentLog(exec.id) }]
  })}
/>

// Horizontal (project phases)
<Timeline
  orientation="horizontal"
  items={[
    { id: '1', timestamp: '2026-Q1', title: 'Planning', status: 'completed', type: 'phase' },
    { id: '2', timestamp: '2026-Q2', title: 'Design', status: 'completed', type: 'phase' },
    { id: '3', timestamp: '2026-Q3', title: 'Construction', status: 'in-progress', type: 'phase' },
    { id: '4', timestamp: '2026-Q4', title: 'Commissioning', status: 'pending', type: 'phase' },
    { id: '5', timestamp: '2027-Q1', title: 'Handover', status: 'pending', type: 'phase' }
  ]}
/>

// Document lifecycle
<Timeline
  items={docEvents.map(e => ({
    id: e.id,
    timestamp: e.timestamp,
    title: e.action,
    description: `${e.documentName} - ${e.details}`,
    type: 'document',
    status: e.status,
    icon: <FileText />,
    color: e.status === 'completed' ? '#22C55E' : '#3B82F6',
    entity: { type: 'document', id: e.docId, label: e.documentName },
    actor: { name: e.userName, avatar: e.userAvatar }
  })}
/>

// Custom content
<Timeline
  items={[
    {
      id: '1',
      timestamp: '2026-01-15',
      title: 'Tender Published',
      content: (
        <Card>
          <CardHeader>
            <Flex justify="between">
              <Text weight="medium">Tender 1298004</Text>
              <Badge variant="success">Published</Badge>
            </Flex>
          </CardHeader>
          <CardContent>
            <Text size="sm">Bridge construction over Karnaphuli River</Text>
            <Flex gap={4} className="mt-2">
              <Button variant="ghost" size="sm">View NIT</Button>
              <Button variant="ghost" size="sm">Download</Button>
            </Flex>
          </CardContent>
        </Card>
      ),
      timestamp: '2026-01-15T10:00:00Z',
      type: 'milestone',
      status: 'completed'
    }
  ]}
/>
```

---

## Type Icons & Colors

| Type | Icon | Default Color |
|------|------|---------------|
| `milestone` | `Flag` | `#8B5CF6` |
| `task` | `CheckSquare` | `#3B82F6` |
| `event` | `Calendar` | `#8B5CF6` |
| `decision` | `Gavel` | `#F59E0B` |
| `document` | `FileText` | `#3B82F6` |
| `meeting` | `Users` | `#22C55E` |
| `agent` | `Bot` | `#8B5CF6` |

---

## Status Colors

| Status | Dot Color | Line Color |
|--------|-----------|------------|
| `completed` | `#22C55E` | `#22C55E` |
| `in-progress` | `#3B82F6` | `#3B82F6` |
| `pending` | `#9CA3AF` | `#E5E7EB` |
| `failed` | `#EF4444` | `#EF4444` |
| `cancelled` | `#6B7280` | `#E5E7EB` |

---

## Future Extensions

- [ ] Grouping by date (day/week/month)
- [ ] Filter by type/status
- [ ] Search/filter
- [ ] Export as PDF
- [ ] Real-time updates
- [ ] Zoom (day/week/month/year)
- [ ] Comparison timeline (plan vs actual)