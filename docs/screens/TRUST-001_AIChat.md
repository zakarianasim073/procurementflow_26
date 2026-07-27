# TRUST-001: AI Assistant Chat Screen Specification

**Module:** `features/ai-chat/AiChatPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Conversational AI interface for querying tender data, getting recommendations, running analyses, and executing agent workflows.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ AiChatHeader (model selector, settings)          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ChatHistory (sidebar, collapsible)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Chat 1: BOQ Analysis for Tender #123       │   │
│          │ │ Chat 2: Competitor Research                 │   │
│          │ │ Chat 3: Pricing Strategy                    │   │
│          │ └────────────────────────────────────────────┘   │
│          ├──────────────────────────────────────────────────┤
│          │ ChatArea (main content)                          │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Message bubbles:                           │   │
│          │ │ User: "Analyze BOQ for tender 123"         │   │
│          │ │ AI: "Analyzing... [typing indicator]"      │   │
│          │ │ AI: "Here's the analysis..." [evidence]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Input area:                                │   │
│          │ │ [Message input...] [Send] [Attach] [Agent] │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ EvidencePanel (AI citations, source documents, confidence)  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AiChatPage
├── ExecutiveHeader
├── AiChatHeader
│   ├── Select (model: gpt-4, claude, etc.)
│   ├── Button (settings)
│   └── Button (new chat)
├── ChatHistory
│   └── ChatSession × N
│       ├── title
│       ├── timestamp
│       └── preview
├── ChatArea
│   ├── MessageList
│   │   └── MessageBubble × N
│   │       ├── Avatar (user/ai)
│   │       ├── content
│   │       ├── EvidencePanel (citations)
│   │       └── timestamp
│   ├── TypingIndicator
│   └── InputArea
│       ├── Textarea (message input)
│       ├── IconButton (attach file)
│       ├── IconButton (run agent)
│       └── Button (send)
└── EvidencePanel
    ├── SourceDocument × N
    ├── ConfidenceBadge
    └── Button (view all sources)
```

## Data Sources

### Chat Sessions
```typescript
// API: GET /api/v1/ai/sessions
interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  model: string;
}

// API: GET /api/v1/ai/sessions/{session_id}/messages
interface ChatMessage {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  agent_result?: AgentResult;
  created_at: string;
}

interface Citation {
  source: string;
  document_id?: string;
  tender_id?: string;
  excerpt: string;
  confidence: number;
}

interface AgentResult {
  agent_id: string;
  status: 'running' | 'completed' | 'failed';
  result?: any;
  error?: string;
}
```

### Send Message
```typescript
// API: POST /api/v1/ai/sessions/{session_id}/messages
interface SendMessageRequest {
  content: string;
  attachments?: string[];
  agent_id?: string;
  context?: {
    tender_id?: string;
    boq_item?: string;
    competitor_id?: string;
  };
}

// WebSocket: ws://localhost:8000/ws/ai/{session_id}
interface WSMessage {
  type: 'token' | 'citation' | 'agent_update' | 'error';
  data: any;
}
```

### React Query
```typescript
const { data: sessions } = useQuery({
  queryKey: ['ai', 'sessions'],
  queryFn: () => api.get('/api/v1/ai/sessions'),
});

const { data: messages } = useQuery({
  queryKey: ['ai', 'sessions', sessionId, 'messages'],
  queryFn: () => api.get(`/api/v1/ai/sessions/${sessionId}/messages`),
  enabled: !!sessionId,
});

const sendMessage = useMutation({
  mutationFn: (request: SendMessageRequest) =>
    api.post(`/api/v1/ai/sessions/${sessionId}/messages`, request),
});
```

## Zustand Store
```typescript
// stores/aiChatStore.ts
interface AiChatState {
  activeSession: string | null;
  inputMessage: string;
  isTyping: boolean;
  selectedModel: string;
  setActiveSession: (id: string | null) => void;
  setInputMessage: (message: string) => void;
  setIsTyping: (typing: boolean) => void;
  setSelectedModel: (model: string) => void;
}
```

## Interactions

### Send Message
1. Type message in input
2. Press Enter or click Send
3. Show user message bubble
4. Show typing indicator
5. Stream AI response via WebSocket
6. Show citations as they arrive
7. Auto-scroll to bottom

### Citation Click
1. Click citation link
2. Open DocumentViewer drawer
3. Highlight cited section
4. Show source document

### Agent Execution
1. Click Agent button
2. Select agent from dropdown
3. Agent runs in background
4. Show progress in chat
5. Display results when complete

### Session Management
1. Click "New Chat" button
2. Create new session
3. Clear chat history
4. Switch between sessions

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | 3-column (history + chat + evidence) |
| Tablet (768-1024px) | 2-column (chat + evidence) |
| Mobile (<768px) | Single column, collapsible panels |

## Loading States
- Sessions: Skeleton list
- Messages: Skeleton bubbles
- Typing: Animated dots

## Error States
- Message failure: Retry button
- Agent failure: Error message in chat
- Network error: Reconnection indicator

## Accessibility
- Messages are focusable
- New messages announced via `aria-live`
- Screen reader: "User said...", "AI said..."
- Keyboard: Enter to send, Shift+Enter for newline

## Telemetry
- `ai_chat.view` — Screen loaded
- `ai_chat.send` — Message sent
- `ai_chat.citation_click` — Citation clicked
- `ai_chat.agent_run` — Agent executed

## Implementation Notes
- WebSocket for streaming responses
- EvidencePanel shows citations in real-time
- AiDock provides quick actions
- Supports file attachments
- Agent integration for complex tasks
