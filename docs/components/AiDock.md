# AiDock Component Contract

**Package**: `widgets/ai`  
**Type**: AI Assistant Panel Component  
**Stability**: Stable  

---

## Purpose

Floating AI assistant dock providing quick access to agent execution, tender intelligence chat, and context-aware recommendations. Transforms from FAB (mobile) to inline panel (desktop ≥ 768px).

---

## Props

```typescript
interface AiDockProps {
  /** Current context for AI */
  context?: {
    tenderId?: string;
    page?: string;
    userRole?: string;
    selectedItems?: string[];
  };
  /** Available agents for quick actions */
  quickAgents?: {
    id: string;
    name: string;
    icon: React.ReactNode;
    description: string;
  }[];
  /** Dock state */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom title/avatar |
| `quickActions` | No | Custom agent buttons |
| `chat` | No | Custom chat interface |
| `footer` | No | Status, version, help |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | Default (mobile) | FAB only |
| `open` | FAB click / desktop | Full panel |
| `loading` | Agent executing | Spinner in FAB/panel |
| `streaming` | AI response | Typing indicator |
| `error` | Execution failed | Error toast in panel |

---

## Accessibility

- **FAB**: `aria-label="Open AI Assistant"`
- **Panel**: `role="dialog"`, `aria-label="AI Assistant"`
- **Focus Trap**: When open on mobile
- **Keyboard**: `Esc` closes, `Tab` cycles
- **Screen Reader**: Announces AI responses

---

## Loading

- **FAB**: Spinner replaces icon
- **Panel**: Skeleton for chat history
- **Agent**: Inline spinner on quick action

---

## Errors

- **No Agents**: "No agents configured"
- **Context Error**: "Unable to load context"
- **Execution Failed**: Inline error with retry

---

## Keyboard

| Key | Action |
|-----|--------|
| `Ctrl+K` / `Ctrl+Shift+A` | Toggle dock |
| `Escape` | Close (mobile) |
| `Tab` | Navigate panel |
| `Enter` | Send message / Run agent |
| `Shift+Enter` | New line in chat |

---

## Mobile

- **< 768px**: 
  - FAB at bottom-right (16px margin)
  - Full-screen drawer on open
  - Swipe down to close
  - Safe area inset handling
- **≥ 768px**: 
  - Inline panel at bottom-right
  - Fixed width (380px)
  - Resizable handle (optional)

---

## Permissions

| Role | Access |
|------|--------|
| `viewer` | Chat only |
| `estimator` | Chat + Quick agents |
| `admin` | Full access |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `ai_dock_open` | `trigger` (fab, shortcut, context) |
| `ai_dock_close` | `duration_ms` |
| `ai_quick_agent_run` | `agent_id`, `context` |
| `ai_chat_message` | `message_length`, `has_context` |

---

## React Query

```typescript
// Quick agents from registry
const { data: agents } = useQuery({
  queryKey: agentKeys.quickActions(context),
  staleTime: 5 * 60 * 1000
});
```

---

## Dependencies

- `Fab` (floating action button)
- `Drawer` / `Panel` (mobile/desktop container)
- `ChatInterface` (conversation UI)
- `QuickAgentGrid` (agent buttons)
- `TypingIndicator` (streaming)
- `lucide-react`: `Bot`, `X`, `Send`, `Mic`, `Paperclip`, `Settings`, `HelpCircle`, `ChevronRight`, `ChevronLeft`, `Maximize`, `Minimize`, `GripVertical`

---

## Layout

### Mobile (Closed)
```
┌─────────────────────────────────┐
│                                 │
│                                 │
│                                 │
│                    ┌───────┐    │
│                    │  🤖  │    │  ← FAB (56×56)
│                    └───────┘    │
└─────────────────────────────────┘
```

### Mobile (Open)
```
┌─────────────────────────────────┐
│ AI Assistant              [✕]   │
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │ Quick Actions               │ │
│ │ [Agent 1] [Agent 2] [Agent 3]│ │
│ │ [Agent 4] [Agent 5] [Agent 6]│ │
│ ├─────────────────────────────┤ │
│ │ Chat                        │ │
│ │ ──────────────────────────  │ │
│ │ 🤖 How can I help?          │ │
│ │ ──────────────────────────  │ │
│ │ [Input...]          [Send]  │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

### Desktop (≥ 768px)
```
┌────────────────────────────────────────┐
│                    ┌──────────────────┐ │
│                    │ AI Assistant [─]  │ │
│                    ├──────────────────┤ │
│                    │ Quick Actions    │ │
│                    │ [A1] [A2] [A3]   │ │
│                    │ [A4] [A5] [A6]   │ │
│                    ├──────────────────┤ │
│                    │ Chat History     │ │
│                    │ ──────────────── │ │
│                    │ 🤖 Hello!        │ │
│                    │ [Input...] [→]   │ │
│                    └──────────────────┘ │
└────────────────────────────────────────┘
```

---

## Future Extensions

- [ ] Voice input (Web Speech API)
- [ ] File attachment in chat
- [ ] Agent chaining visualization
- [ ] Conversation history persistence
- [ ] Multi-language support
- [ ] Offline mode with sync