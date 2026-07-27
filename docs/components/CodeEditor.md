# CodeEditor Component Contract

**Module:** `shared/ui/CodeEditor`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Syntax-highlighted code editor for viewing/editing AI agent configurations, webhook payloads, SQL queries, and JSON schema definitions.

## Props
```typescript
interface CodeEditorProps {
  value: string;
  onChange?: (value: string) => void;
  language?: 'json' | 'sql' | 'python' | 'yaml' | 'markdown' | 'javascript';
  readOnly?: boolean;
  lineNumbers?: boolean;
  wordWrap?: boolean;
  minimap?: boolean;
  height?: number | string;
  width?: number | string;
  theme?: 'light' | 'dark' | 'system';
  fontSize?: number;
  tabSize?: number;
  showErrors?: boolean;
  decorations?: Decoration[];
  className?: string;
  testId?: string;
}

interface Decoration {
  range: { startLine: number; startCol: number; endLine: number; endCol: number };
  type: 'error' | 'warning' | 'info' | 'highlight';
  message?: string;
}
```

## Slots
- `header` — Toolbar above editor (language selector, actions)
- `footer` — Status bar (line/col, language, encoding)
- `gutter` — Custom gutter decorations

## State
```typescript
interface CodeEditorState {
  cursorPosition: { line: number; column: number };
  selection: { start: Position; end: Position } | null;
  diagnostics: Diagnostic[];
}
```

## Accessibility
- **ARIA:** `role="textbox"`, `aria-multiline="true"`, `aria-readonly`
- **Keyboard:** Standard editor shortcuts (Ctrl+Z undo, Ctrl+F find, etc.)
- **Focus:** Managed by Monaco/CodeMirror

## Loading
- Skeleton with line placeholders during initialization

## Errors
- Inline error markers with hover tooltips
- Error count in status bar

## Keyboard
| Key | Action |
|-----|--------|
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+F | Find |
| Ctrl+H | Find & Replace |
| Tab | Insert indent |
| Shift+Tab | Outdent |
| Ctrl+/ | Toggle comment |
| Ctrl+Shift+F | Format document |

## Mobile
- Read-only mode with zoom
- Virtual keyboard-aware height
- Simplified toolbar (no keyboard shortcuts)

## Permissions
- `readOnly` when user lacks edit permission
- Validation before save

## Telemetry
- `code_editor.open` — Editor opened (language, readOnly)
- `code_editor.save` — Content saved

## React Query
- Fetches initial content via query
- Mutations for save operations

## Dependencies
- Monaco Editor (`@monaco-editor/react`) or CodeMirror
- `shared/ui/Skeleton` — Loading state

## Future Extensions
- Collaborative editing (CRDT)
- AI code completion
- Diff viewer mode
- Custom language support
