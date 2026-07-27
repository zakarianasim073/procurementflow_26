# VersionHistory Component Contract

**Package**: `widgets/history`  
**Type**: Version Control Component  
**Stability**: Stable  

---

## Purpose

Version history viewer with diff visualization, rollback, and comparison for documents, BOQs, reports, and tender configurations.

---

## Props

```typescript
interface VersionHistoryProps {
  /** Current version */
  currentVersion: number;
  /** Version history */
  versions: Version[];
  /** Version click handler */
  onVersionSelect?: (version: Version) => void;
  /** Restore handler */
  onRestore?: (version: Version) => void;
  /** Compare handler */
  onCompare?: (v1: Version, v2: Version) => void;
  /** Delete handler */
  onDelete?: (version: Version) => void;
  /** Current content (for comparison) */
  currentContent?: string;
  /** Content getter for version */
  getContent?: (version: Version) => Promise<string>;
  /** Diff function */
  diff?: (oldText: string, newText: string) => DiffResult;
  /** Custom className */
  className?: string;
}

interface Version {
  id: string;
  version: number;
  timestamp: Date | string;
  author: {
    id: string;
    name: string;
    avatar?: string;
  };
  message: string;
  changes?: {
    additions: number;
    deletions: number;
    modifications: number;
  };
  tags?: string[];
  metadata?: Record<string, any>;
}

interface DiffResult {
  added: string[];
  removed: string[];
  modified: { old: string; new: string }[];
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `item` | No | Custom version row |
| `diff` | No | Custom diff view |
| `actions` | No | Custom actions per version |
| `empty` | No | Empty state |

---

## State

| State | Visual |
|-------|--------|
| `loading` | Skeleton rows |
| `comparing` | Diff view open |
| `restoring` | Spinner on restore button |
| `error` | Toast/error banner |

---

## Accessibility

- **Role**: `list` with `role="listitem"` items
- **ARIA**: `aria-current` on current version
- **Keyboard**: Arrow keys navigate, Enter selects
- **Screen Reader**: Announces version changes

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Up/Down` | Navigate versions |
| `Enter` | Select version |
| `C` | Compare selected with current |
| `R` | Restore version |
| `D` | Delete version |
| `Escape` | Close diff view |

---

## Usage Examples

```tsx
// Document version history
<VersionHistory
  currentVersion={5}
  versions={documentVersions}
  currentContent={documentContent}
  getContent={async (v) => fetchDocumentVersion(v.id)}
  diff={computeDiff}
  onVersionSelect={(v) => openVersionPreview(v)}
  onRestore={(v) => confirmRestore(v)}
  onCompare={(v1, v2) => openDiff(v1, v2)}
  onDelete={(v) => confirmDelete(v)}
/>

// BOQ comparison
<VersionHistory
  currentVersion={boq.currentVersion}
  versions={boq.versions}
  currentContent={boq.content}
  getContent={async (v) => fetchBOQVersion(v.id)}
  diff={diffBOQ}
  onCompare={(v1, v2) => openBOQDiff(v1, v2)}
/>

// Configuration history
<VersionHistory
  currentVersion={config.version}
  versions={configHistory}
  onRestore={(v) => restoreConfig(v)}
  onCompare={(v1, v2) => showConfigDiff(v1, v2)}
/>
```

---

## Diff View

```tsx
// Side-by-side diff
<DiffView
  oldText={oldVersion.content}
  newText={newVersion.content}
  mode="side-by-side" // or 'inline'
  contextLines={3}
  onChange={(change) => navigateToChange(change)}
/>

// Inline diff
<DiffView
  oldText={oldContent}
  newText={newContent}
  mode="inline"
  highlightChanges
/>

// Word-level diff
<DiffView
  oldText={oldText}
  newText={newText}
  granularity="word" // or 'char', 'line'
/>
```

---

## Version Tags

```tsx
<VersionTag version={v} />
// Renders: v3.2.1-beta
// With badges: [MAJOR] [MINOR] [PATCH] [PRE-RELEASE]
```

---

## Comparison Modes

| Mode | Description |
|------|-------------|
| `side-by-side` | Two panels, synchronized scroll |
| `inline` | Single view with inline markers |
| `unified` | Unified diff format |
| `word` | Word-level highlighting |
| `line` | Line-level highlighting |

---

## Future Extensions

- [ ] Three-way merge
- [ ] Conflict resolution UI
- [ ] Branching visualization
- [ ] Automated changelog generation
- [ ] Semantic versioning enforcement
- [ ] Webhook notifications
- [ ] Export diff as patch
- [ ] Collaborative review