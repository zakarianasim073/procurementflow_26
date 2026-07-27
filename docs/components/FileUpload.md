# FileUpload Component Contract

**Package**: `widgets/files`  
**Type**: File Input Component  
**Stability**: Stable  

---

## Purpose

Drag-and-drop file upload with progress, validation, preview, and chunked upload support. Used for BOQ, tender documents, and report attachments.

---

## Props

```typescript
interface FileUploadProps {
  /** Accepted file types */
  accept?: string[]; // MIME types or extensions
  /** Max file size (bytes) */
  maxSize?: number; // default: 50MB
  /** Max files */
  maxFiles?: number; // default: 10
  /** Multiple files */
  multiple?: boolean;
  /** Upload endpoint */
  uploadUrl?: string;
  /** Upload headers */
  headers?: Record<string, string>;
  /** Upload method */
  method?: 'POST' | 'PUT' | 'PATCH';
  /** Form data key */
  fieldName?: string; // default: 'file'
  /** Additional form data */
  formData?: Record<string, string>;
  /** Chunked upload */
  chunked?: boolean;
  /** Chunk size (bytes) */
  chunkSize?: number; // default: 5MB
  /** Progress callback */
  onProgress?: (file: UploadFile, progress: number) => void;
  /** Success callback */
  onSuccess?: (file: UploadFile, response: any) => void;
  /** Error callback */
  onError?: (file: UploadFile, error: Error) => void;
  /** Complete callback */
  onComplete?: (files: UploadFile[]) => void;
  /** Custom className */
  className?: string;
}

interface UploadFile {
  id: string;
  file: File;
  preview?: string;
  status: 'pending' | 'uploading' | 'success' | 'error' | 'cancelled';
  progress: number;
  error?: string;
  response?: any;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `trigger` | No | Custom dropzone trigger |
| `fileItem` | No | Custom file row |
| `progress` | No | Custom progress bar |
| `actions` | No | Custom file actions |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `idle` | Initial | Dropzone |
| `dragover` | Drag enter | Highlighted border |
| `uploading` | Upload started | Progress bars |
| `success` | All complete | Checkmarks |
| `error` | Any failed | Red borders, retry |
| `mixed` | Some complete | Partial checkmarks |

---

## Accessibility

- **Role**: `region` with `aria-label="File upload"`
- **Dropzone**: `role="button"`, `aria-dropeffect="copy"`
- **Files**: `role="list"`, `aria-label="Uploaded files"`
- **Progress**: `role="progressbar"` with `aria-valuenow`
- **Keyboard**: Tab to trigger, Enter to select files

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus trigger |
| `Enter` / `Space` | Open file dialog |
| `Escape` | Cancel upload / Close dialog |
| `Delete` | Remove file (focused) |

---

## Loading

- **File List**: Skeleton rows
- **Progress**: Animated bar during upload

---

## Errors

- **Type**: "File type not allowed"
- **Size**: "File exceeds maximum size (50MB)"
- **Count**: "Maximum 10 files allowed"
- **Network**: "Upload failed — [Retry]"
- **Server**: Server error message

---

## Mobile

- **Camera**: Capture attribute for images
- **Touch**: Tap to select, long press for options
- **Progress**: Full-width bars
- **Swipe**: Swipe to delete

---

## Permissions

| Role | Upload |
|------|--------|
| `viewer` | ❌ |
| `estimator` | ✅ |
| `admin` | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `file_upload_start` | `file_count`, `total_size`, `types` |
| `file_upload_progress` | `file_id`, `progress` |
| `file_upload_complete` | `file_id`, `duration_ms`, `status` |
| `file_upload_error` | `file_id`, `error_type` |

---

## React Query

```typescript
const { mutate: upload } = useMutation(uploadFiles, {
  onMutate: (files) => files.forEach(f => setProgress(f.id, 0)),
  onSuccess: (data, files) => files.forEach(f => setProgress(f.id, 100)),
  onError: (error, files) => files.forEach(f => setError(f.id, error.message))
});
```

---

## Dependencies

- `axios` / `fetch` (upload)
- `Progress` (progress bar)
- `FileIcon` (file type icons)
- `Button` (actions)
- `lucide-react`: `Upload`, `X`, `Download`, `Eye`, `RotateCw`, `AlertCircle`, `CheckCircle`, `Loader2`, `Trash2`, `File`, `Image`, `FileText`, `FileSpreadsheet`

---

## Usage Examples

```tsx
// Basic BOQ upload
<FileUpload
  accept={['.pdf', '.xlsx', '.xls', '.docx', '.doc']}
  maxSize={50 * 1024 * 1024}
  maxFiles={5}
  uploadUrl="/api/boq/upload"
  onSuccess={(file, res) => {
    setBoqFileId(res.file_id);
    toast.success(`${file.name} uploaded`);
  }}
/>

// Chunked large files
<FileUpload
  chunked
  chunkSize={5 * 1024 * 1024}
  maxSize={500 * 1024 * 1024}
  uploadUrl="/api/upload/chunked"
/>

// With custom preview
<FileUpload
  renderFileItem={(file, { remove, retry, preview }) => (
    <FileRow
      file={file}
      onRemove={remove}
      onRetry={retry}
      onPreview={preview}
    />
  )}
/>

// Tender documents
<FileUpload
  accept={['.pdf', '.docx', '.doc', '.jpg', '.png']}
  multiple
  maxFiles={20}
  uploadUrl="/api/tender/documents"
  formData={{ tender_id: tenderId }}
  onComplete={(files) => {
    const uploaded = files.filter(f => f.status === 'success');
    toast.success(`${uploaded.length} documents uploaded`);
  }}
/>
```

---

## File Type Icons

```typescript
const FILE_ICONS = {
  'application/pdf': FileText,
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileSpreadsheet,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileText,
  'application/msword': FileText,
  'image/': Image,
  'text/': FileText,
  'default': File
};
```

---

## Future Extensions

- [ ] Folder upload (webkitdirectory)
- [ ] Resume interrupted uploads
- [ ] S3 direct upload (presigned)
- [ ] Image crop/rotate before upload
- [ ] Virus scan integration
- [ ] Duplicate detection
- [ ] Upload queue management