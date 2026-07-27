# FileExplorer Component Contract

**Package**: `widgets/files`  
**Type**: File Management Component  
**Stability**: Stable  

---

## Purpose

File browser with tree navigation, grid/list views, search, multi-select, and bulk operations. Used for tender document management, BOQ archives, and report repositories.

---

## Props

```typescript
interface FileExplorerProps {
  /** Root path */
  rootPath: string;
  /** Current path */
  currentPath: string;
  /** Path change handler */
  onPathChange: (path: string) => void;
  /** Files/folders data */
  items: FileItem[];
  /** Loading state */
  loading?: boolean;
  /** Selection */
  selectedItems?: string[];
  onSelectionChange?: (ids: string[]) => void;
  /** View mode */
  viewMode?: 'grid' | 'list' | 'tree';
  onViewModeChange?: (mode: string) => void;
  /** Sort */
  sortBy?: 'name' | 'size' | 'modified' | 'type';
  sortOrder?: 'asc' | 'desc';
  onSortChange?: (by: string, order: 'asc' | 'desc') => void;
  /** Actions */
  onDownload?: (items: FileItem[]) => void;
  onDelete?: (items: FileItem[]) => void;
  onRename?: (item: FileItem, newName: string) => void;
  onMove?: (items: FileItem[], targetPath: string) => void;
  onUpload?: (files: File[], targetPath: string) => void;
  /** Permissions */
  canUpload?: boolean;
  canDelete?: boolean;
  canRename?: boolean;
  canMove?: boolean;
  canDownload?: boolean;
  /** Custom className */
  className?: string;
}

interface FileItem {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'folder';
  size?: number;
  mimeType?: string;
  modifiedAt: Date | string;
  createdAt?: Date | string;
  permissions?: {
    read: boolean;
    write: boolean;
    delete: boolean;
  };
  thumbnail?: string;
  metadata?: Record<string, any>;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `toolbar` | No | Custom toolbar (view, sort, actions) |
| `breadcrumb` | No | Custom breadcrumb |
| `item` | No | Custom item rendering |
| `contextMenu` | No | Custom context menu |
| `upload` | No | Custom upload zone |
| `empty` | No | Empty folder state |

---

## State

| State | Visual |
|-------|--------|
| `loading` | Skeleton items |
| `empty` | "This folder is empty" |
| `selecting` | Checkboxes visible |
| `dragging` | Drag preview |
| `uploading` | Progress bars |
| `renaming` | Inline input |
| `error` | Toast/error banner |

---

## Accessibility

- **Role**: `tree` (tree view) / `grid` (list/grid)
- **ARIA**: `aria-selected`, `aria-expanded` (folders)
- **Keyboard**: Full tree/grid navigation
- **Screen Reader**: Announces selection, actions

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Keys` | Navigate |
| `Enter` | Open file/folder |
| `Space` | Toggle selection |
| `Ctrl+A` | Select all |
| `Delete` | Delete selected |
| `F2` | Rename |
| `Ctrl+C` / `Ctrl+V` | Copy/Paste |
| `Ctrl+X` | Cut |
| `Escape` | Clear selection / Close menu |
| `Context Menu` / `Shift+F10` | Context menu |

---

## Usage Examples

```tsx
// Tender documents
<FileExplorer
  rootPath="/tenders/1298004"
  currentPath={currentPath}
  onPathChange={setCurrentPath}
  items={documents}
  viewMode={viewMode}
  onViewModeChange={setViewMode}
  selectedItems={selectedIds}
  onSelectionChange={setSelectedIds}
  onDownload={handleDownload}
  onDelete={handleDelete}
  onRename={handleRename}
  onMove={handleMove}
  onUpload={handleUpload}
  canUpload={canUpload}
  canDelete={canDelete}
  canRename={canRename}
  canMove={canMove}
/>

// BOQ archive
<FileExplorer
  rootPath="/boq/archive"
  currentPath={boqPath}
  onPathChange={setBoqPath}
  items={boqFiles}
  viewMode="list"
  sortBy="modified"
  sortOrder="desc"
  onDownload={downloadBOQ}
  onDelete={deleteBOQ}
/>

// Report repository
<FileExplorer
  rootPath="/reports"
  currentPath={reportPath}
  onPathChange={setReportPath}
  items={reports}
  viewMode="grid"
  onDownload={downloadReport}
  onDelete={deleteReport}
  canUpload={isAdmin}
  canDelete={isAdmin}
/>
```

---

## Context Menu Actions

```tsx
const contextMenuItems = (item: FileItem) => [
  { label: 'Open', icon: <Eye />, action: () => open(item), disabled: item.type === 'folder' },
  { label: 'Download', icon: <Download />, action: () => download([item]), disabled: item.type === 'folder' },
  { divider: true },
  { label: 'Rename', icon: <Edit />, action: () => startRename(item), disabled: !canRename },
  { label: 'Move', icon: <Move />, action: () => startMove(item), disabled: !canMove },
  { label: 'Copy', icon: <Copy />, action: () => copyToClipboard(item) },
  { divider: true },
  { label: 'Delete', icon: <Trash2 />, action: () => confirmDelete([item]), danger: true, disabled: !canDelete },
  { label: 'Properties', icon: <Info />, action: () => openProperties(item) },
);
```

---

## Upload Zone

```tsx
<UploadZone
  accept={['.pdf', '.xlsx', '.docx', '.jpg', '.png']}
  maxFiles={20}
  maxSize={100 * 1024 * 1024}
  onUpload={async (files) => {
    for (const file of files) {
      await uploadFile(file, currentPath);
    }
  }}
  onProgress={(file, progress) => setUploadProgress(file.name, progress)}
/>
```

---

## View Modes

| Mode | Layout | Best For |
|------|--------|----------|
| `grid` | Thumbnails | Images, documents |
| `list` | Compact rows | Documents, details |
| `tree` | Hierarchical | Folder navigation |

---

## Sorting

| Field | Default Order |
|-------|---------------|
| `name` | asc |
| `size` | desc |
| `modified` | desc |
| `type` | asc (folders first) |

---

## Future Extensions

- [ ] Drag-and-drop upload
- [ ] Folder upload (webkitdirectory)
- [ ] Zip download
- [ ] Version history
- [ ] Tags/labels
- [ ] Comments/annotations
- [ ] OCR search
- [ ] Virus scan integration
- [ ] Access control lists (ACL)