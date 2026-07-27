# ImageCropper Component Contract

**Package**: `widgets/media`  
**Type**: Media Component  
**Stability**: Stable  

---

## Purpose

Client-side image cropping with aspect ratio constraints, rotation, zoom, and touch support. Used for avatar uploads, document scans, and thumbnail generation.

---

## Props

```typescript
interface ImageCropperProps {
  /** Source image */
  src: string; // URL, blob, or data URL
  /** Initial crop area */
  crop?: CropArea;
  /** Aspect ratio (width/height) */
  aspect?: number | 'free' | 'square' | '16:9' | '4:3' | '3:2' | '2:3' | '3:4' | '9:16';
  /** Output format */
  outputType?: 'blob' | 'dataurl' | 'file';
  /** Output quality (0-1) */
  quality?: number; // default: 0.92
  /** Output format */
  format?: 'jpeg' | 'png' | 'webp';
  /** Max output dimensions */
  maxWidth?: number;
  maxHeight?: number;
  /** Min crop size */
  minCropWidth?: number;
  minCropHeight?: number;
  /** Show grid overlay */
  showGrid?: boolean;
  /** Allow rotation */
  rotatable?: boolean; // default: true
  /** Allow zoom */
  zoomable?: boolean; // default: true
  /** Crop area change handler */
  onCropChange?: (crop: CropArea) => void;
  /** Crop complete handler */
  onCropComplete?: (croppedImage: Blob | string, crop: CropArea) => void;
  /** Error handler */
  onError?: (error: Error) => void;
  /** Custom className */
  className?: string;
}

interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
  rotate?: number; // degrees
  scaleX?: number;
  scaleY?: number;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `toolbar` | No | Custom toolbar actions |
| `overlay` | No | Custom crop overlay |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `loading` | `src` loading | Skeleton |
| `ready` | Image loaded | Cropper ready |
| `cropping` | Drag/resize | Active crop area |
| `rotating` | Rotate button | Rotation UI |
| `processing` | Crop complete | Spinner overlay |
| `error` | Load/crop failed | Error message |

---

## Accessibility

- **Role**: `application` with `aria-label="Image cropper"`
- **Keyboard**: Full keyboard navigation
- **Screen Reader**: Announces crop changes
- **Focus**: Visible focus ring on controls

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Keys` | Move crop area (1px) |
| `Shift + Arrow` | Resize crop area |
| `R` | Rotate 90° CW |
| `Shift + R` | Rotate 90° CCW |
| `Z` | Zoom in |
| `Shift + Z` | Zoom out |
| `0` | Reset crop |
| `Escape` | Cancel |
| `Enter` | Confirm crop |

---

## Mobile

- **Touch**: Drag to move, pinch to zoom, two-finger rotate
- **Gestures**: Double-tap to zoom to fit
- **Toolbar**: Bottom sheet on < 640px
- **Safe Area**: Respects bottom inset

---

## Usage Examples

```tsx
// Basic avatar cropper
<ImageCropper
  src={avatarFile}
  aspect={1}
  maxWidth={512}
  maxHeight={512}
  onCropComplete={(blob, crop) => {
    setAvatarBlob(blob);
    setCropArea(crop);
  }}
/>

// Document scanner (A4)
<ImageCropper
  src={docFile}
  aspect={210/297} // A4
  rotatable
  onCropComplete={(blob) => uploadScan(blob)}
/>

// Banner crop (16:9)
<ImageCropper
  src={bannerFile}
  aspect={16/9}
  minCropWidth={800}
  minCropHeight={450}
  onCropComplete={(blob) => setBanner(blob)}
/>

// Free form with grid
<ImageCropper
  src={imageFile}
  aspect="free"
  showGrid
  rotatable
  zoomable
  onCropComplete={(blob, crop) => saveCrop(blob, crop)}
/>

// With custom toolbar
<ImageCropper
  src={imageFile}
  aspect={4/3}
  toolbar={
    <CropToolbar
      onRotate={handleRotate}
      onFlip={handleFlip}
      onReset={handleReset}
      onDownload={handleDownload}
    />
  }
  onCropComplete={handleCropComplete}
/>
```

---

## Toolbar Actions

```tsx
interface CropToolbarProps {
  onRotate?: (degrees: number) => void;
  onFlip?: (horizontal: boolean, vertical: boolean) => void;
  onReset?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onDownload?: () => void;
  onConfirm?: () => void;
  onCancel?: () => void;
  disabled?: boolean;
}
```

---

## Output Handling

```tsx
const handleCropComplete = async (blob: Blob, crop: CropArea) => {
  // Convert to file
  const file = new File([blob], 'cropped-image.jpg', { type: 'image/jpeg' });
  
  // Upload
  const formData = new FormData();
  formData.append('file', file);
  formData.append('crop', JSON.stringify(crop));
  
  const res = await fetch('/api/upload/crop', {
    method: 'POST',
    body: formData
  });
  
  // Preview
  const previewUrl = URL.createObjectURL(blob);
  setPreview(previewUrl);
};
```

---

## Mobile Touch Gestures

| Gesture | Action |
|---------|--------|
| One finger drag | Move crop area |
| Two finger pinch | Zoom in/out |
| Two finger rotate | Rotate image |
| Double tap | Zoom to fit / reset |
| Long press | Context menu |

---

## Performance

- **Canvas**: Offscreen rendering for smooth interaction
- **Web Workers**: Heavy operations (rotate, large images)
- **Memory**: Auto-cleanup on unmount
- **Max dimensions**: 4096×4096 (browser limit)

---

## Future Extensions

- [ ] AI-powered auto-crop (face/edge detection)
- [ ] Perspective correction
- [ ] Batch crop (multiple images)
- [ ] Preset templates (passport, ID card, etc.)
- [ ] Watermark overlay
- [ ] EXIF orientation handling
- [ ] HEIC/AVIF support