# ActivityTimeline Component Contract

**Package**: `widgets/ai`  
**Type**: Activity Display Component  
**Stability**: Stable  

---

## Purpose

Displays chronological activity feed for tenders, agents, and user actions. Used in TEN-001 through TEN-005 screens, executive reports, and agent execution history.

---

## Props

```typescript
interface ActivityTimelineProps {
  /** Activity items */
  items: ActivityItem[];
  /** Timeline configuration */
  config?: {
    /** Group by date */
    groupByDate?: boolean;
    /** Show timestamps */
    showTimestamps?: boolean;
    /** Show user avatars */
    showAvatars?: boolean;
    /** Max items before "Load more" */
    maxItems?: number;
    /** Real-time updates */
    realtime?: boolean;
  };
  /** Load more handler */
  onLoadMore?: () => void;
  /** Item click handler */
  onItemClick?: (item: ActivityItem) => void;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string;
  /** Custom className */
  className?: string;
}

interface ActivityItem {
  id: string;
  type: 'tender_created' | 'tender_updated' | 'document_uploaded' | 
        'boq_compared' | 'agent_executed' | 'agent_completed' | 
        'agent_failed' | 'report_generated' | 'notification_sent' | 
        'user_action' | 'system_event';
  title: string;
  description?: string;
  timestamp: string; // ISO 8601
  user?: {
    id: string;
    name: string;
    avatar?: string;
    role: string;
  };
  agent?: {
    id: string;
    name: string;
  };
  tender?: {
    id: string;
    tenderNo: string;
  };
  metadata?: Record<string, any>;
  status?: 'success' | 'warning' | 'error' | 'info' | 'pending';
  links?: { label: string; url: string }[];
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `item` | No | Custom item rendering |
| `groupHeader` | No | Custom date group header |
| `empty` | No | Empty state |
| `loadMore` | No | Custom load more button |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `loading` | `loading=true` | Skeleton items (3) |
| `empty` | `items.length === 0` | Illustration + message |
| `error` | `error` prop | Alert + retry |
| `realtime` | `realtime=true` + new item | Slide-in animation |
| `grouped` | `groupByDate=true` | Date separators |

---

## Accessibility

- **Role**: `list` with `aria-label="Activity timeline"`
- **Items**: `role="listitem"` with `aria-label="[type] at [time]"`
- **Timestamps**: `<time>` element with `dateTime`
- **Keyboard**: Tab through items, Enter opens details
- **Screen Reader**: Announces new items in realtime mode

---

## Loading

- **Skeleton**: 3 items with shimmer
- **Delay**: 150ms

---

## Errors

- **Load Failed**: "Unable to load activity — [Retry]"
- **Realtime Disconnected**: "Live updates paused — [Reconnect]"

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate items |
| `Enter` | Open item details |
| `Escape` | Close details |
| `↑/↓` | Navigate items |

---

## Mobile

- **< 640px**: Compact items, swipe for actions
- **Timestamps**: Relative format ("2h ago")
- **Avatars**: Smaller (24px)
- **Load More**: Button at bottom

---

## Permissions

| Role | View |
|------|------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `activity_timeline_view` | `item_count`, `grouped` |
| `activity_item_click` | `item_id`, `type` |
| `activity_load_more` | `page`, `total` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: ['activity', tenderId],
  queryFn: () => fetchActivity(tenderId),
  refetchInterval: config.realtime ? 30000 : false
});
```

---

## Dependencies

- `RelativeTime` (for timestamps)
- `Avatar` (for user/agent)
- `Badge` (for status)
- `Icon` (type-specific icons)
- `Button` (for links)
- `Skeleton` (loading)
- `lucide-react`: `Clock`, `User`, `Bot`, `FileText`, `CheckCircle`, `AlertCircle`, `Info`, `Loader`, `ChevronRight`, `ExternalLink`

---

## Type Icons

| Type | Icon | Color |
|------|------|-------|
| `tender_created` | `PlusCircle` | Green |
| `document_uploaded` | `FileText` | Blue |
| `boq_compared` | `Table` | Purple |
| `agent_executed` | `Play` | Blue |
| `agent_completed` | `CheckCircle` | Green |
| `agent_failed` | `XCircle` | Red |
| `report_generated` | `FileOutput` | Indigo |
| `user_action` | `User` | Gray |
| `system_event` | `Cpu` | Orange |

---

## Layout Structure

```
┌─────────────────────────────────────┐
│  TODAY                              │ ← Date group
├─────────────────────────────────────┤
│ ● 14:32  BOQ Compared               │
│   Tender 1298004 compared vs BWDB   │
│   Agent: BOQ Intelligence Agent     │
│   [View Details]              2m ago│
├─────────────────────────────────────┤
│ ● 13:45  Document Uploaded          │
│   TDS uploaded for Tender 1298004   │
│   User: John Doe (Estimator)        │
│   [View Document]            45m ago│
├─────────────────────────────────────┤
│  YESTERDAY                          │
├─────────────────────────────────────┤
│ ● 16:20  Agent Completed            │
│   Win Probability Agent finished    │
│   Confidence: 71% (High)            │
│   [View Report]              1d ago │
└─────────────────────────────────────┘
```

---

## Future Extensions

- [ ] Filter by type/user/date
- [ ] Export as CSV/PDF
- [ ] Real-time WebSocket integration
- [ ] Activity search
- [ ] Correlation view (related activities)
- [ ] Digest email generation