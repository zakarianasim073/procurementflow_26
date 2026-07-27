# MarkdownViewer Component Contract

**Module:** `shared/ui/MarkdownViewer`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Rendered markdown display for tender specifications, knowledge base articles, agent reasoning logs, and system documentation.

## Props
```typescript
interface MarkdownViewerProps {
  content: string;
  variant?: 'prose' | 'compact' | 'raw';
  sanitize?: boolean;
  enableTables?: boolean;
  enableCodeHighlight?: boolean;
  enableMath?: boolean;
  enableDiagrams?: boolean;
  onLinkClick?: (url: string) => void;
  onImageClick?: (src: string) => void;
  className?: string;
  testId?: string;
}

interface MarkdownViewerToolbarProps {
  onCopy?: () => void;
  onDownload?: (format: 'md' | 'html' | 'pdf') => void;
  onPrint?: () => void;
  className?: string;
}
```

## Slots
- `content` — Rendered markdown body
- `toolbar` — Action buttons (copy, download, print)
- `codeBlock` — Custom code block renderer
- `table` — Custom table renderer

## State
```typescript
interface MarkdownViewerState {
  isCopied: boolean;
  expandedCodeBlocks: Set<number>;
  toc: TocItem[];
}

interface TocItem {
  id: string;
  title: string;
  level: number;
}
```

## Accessibility
- **ARIA:** `role="article"`, heading hierarchy maintained
- **Keyboard:** Link navigation with Enter, code block copy with Ctrl+C
- **Focus:** Visible focus on interactive elements

## Loading
- N/A — synchronous rendering

## Errors
- Fallback to plain text on parse failure
- Broken image placeholder

## Keyboard
| Key | Action |
|-----|--------|
| Enter | Follow focused link |
| Ctrl+C | Copy code block when focused |
| Ctrl+Shift+C | Copy rendered content |

## Mobile
- Responsive tables with horizontal scroll
- Collapsed code blocks with tap-to-expand
- Reduced heading sizes

## Permissions
- No restrictions — read-only display

## Telemetry
- `markdown.link_click` — External link clicked
- `markdown.code_copy` — Code block copied

## React Query
- None — pure rendering

## Dependencies
- `react-markdown` for parsing
- `remark-gfm` for GitHub-flavored markdown
- `rehype-highlight` for syntax highlighting
- `rehype-sanitize` for XSS protection

## Future Extensions
- Table of contents generation
- Search within document
- Annotation/highlighting
- Collaborative commenting
