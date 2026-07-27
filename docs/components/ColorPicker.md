# ColorPicker Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Color selection input with palette, custom colors, format conversion, and accessibility support. Used for theme customization, tag colors, chart theming, and status indicators.

---

## Props

```typescript
interface ColorPickerProps {
  /** Selected color */
  value: string; // hex, rgb, hsl, or named
  /** Change handler */
  onChange: (color: string, format: 'hex' | 'rgb' | 'hsl') => void;
  /** Display format */
  format?: 'hex' | 'rgb' | 'hsl' | 'auto'; // default: 'hex'
  /** Predefined palette */
  palette?: string[]; // hex colors
  /** Show palette */
  showPalette?: boolean; // default: true
  /** Show sliders */
  showSliders?: boolean; // default: true
  /** Show input field */
  showInput?: boolean; // default: true
  /** Show alpha slider */
  showAlpha?: boolean; // default: false
  /** Predefined colors only (no custom) */
  presetOnly?: boolean;
  /** Disabled */
  disabled?: boolean;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `swatch` | No | Custom color swatch |
| `input` | No | Custom input field |
| `palette` | No | Custom palette rendering |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Swatch + input |
| `open` | Click swatch | Popover with palette/sliders |
| `sliders` | Tab to sliders | HSV/RGB sliders visible |
| `alpha` | Alpha enabled | Alpha slider visible |
| `disabled` | `disabled=true` | Muted, not clickable |
| `error` | Invalid format | Red border on input |

---

## Accessibility

- **Role**: `dialog` (popover), `slider` (hue/saturation/value/alpha)
- **ARIA**: `aria-label`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- **Keyboard**: Full keyboard navigation
- **Screen Reader**: Announces color changes
- **Contrast**: Meets WCAG AA for all default palette colors

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate: swatch → palette → sliders → input → close |
| `Enter` / `Space` | Open/close popover |
| `Arrow Keys` | Navigate palette / adjust sliders |
| `Escape` | Close popover |
| `Tab` (in popover) | Cycle focusable elements |
| `Home` / `End` | Min/max slider value |

---

## Usage Examples

```tsx
// Basic
<ColorPicker
  value={themeColor}
  onChange={setThemeColor}
  format="hex"
/>

// With alpha
<ColorPicker
  value={accentColor}
  onChange={setAccentColor}
  showAlpha
  format="rgb"
/>

// Preset palette only
<ColorPicker
  value={tagColor}
  onChange={setTagColor}
  palette={TAG_COLORS}
  presetOnly
  showSliders={false}
/>

// Custom palette
<ColorPicker
  value={chartColor}
  onChange={setChartColor}
  palette={[
    '#3B82F6', '#22C55E', '#F59E0B', '#EF4444',
    '#8B5CF6', '#EC4899', '#06B6D4', '#F97316'
  ]}
/>

// With custom format display
<ColorPicker
  value={statusColor}
  onChange={setStatusColor}
  format="hsl"
  onChange={(color, format) => {
    setStatusColor(color);
    setStatusColorFormat(format);
  }}
/>

// Trigger as button
<ColorPicker
  value={themeColor}
  onChange={setThemeColor}
  renderSwatch={(color, open, toggle) => (
    <Button
      variant="outline"
      onClick={toggle}
      style={{ backgroundColor: color }}
      className="w-10 h-10"
    >
      <Palette className="w-5 h-5" />
    </Button>
  )}
/>
```

---

## Default Palette

```typescript
const DEFAULT_PALETTE = [
  // Blues
  '#3B82F6', '#1D4ED8', '#1E40AF', '#1E3A8A',
  // Greens
  '#22C55E', '#16A34A', '#15803D', '#166534',
  // Amber/Yellow
  '#F59E0B', '#D97706', '#B45309', '#92400E',
  // Reds
  '#EF4444', '#DC2626', '#B91C1C', '#991B1B',
  // Purples
  '#8B5CF6', '#7C3AED', '#6D28D9', '#5B21B6',
  // Pinks
  '#EC4899', '#DB2777', '#BE185D', '#9D174D',
  // Cyans
  '#06B6D4', '#0891B2', '#0E7490', '#155E75',
  // Oranges
  '#F97316', '#EA580C', '#C2410C', '#9A3412',
  // Grays
  '#6B7280', '#4B5563', '#374151', '#1F2937',
  // White/Black
  '#FFFFFF', '#000000',
];
```

---

## Format Conversion

```typescript
// Internal: always store as hex with alpha
// Display: user-selected format

// Hex: #RRGGBB or #RRGGBBAA
// RGB: rgb(r, g, b) / rgba(r, g, b, a)
// HSL: hsl(h, s%, l%) / hsla(h, s%, l%, a)

// Conversion utilities provided:
import { hexToRgb, rgbToHsl, hslToHex, parseColor } from '@/lib/color';

// Example:
const rgb = parseColor('#3B82F6'); // { r: 59, g: 130, b: 246, a: 1 }
const hsl = rgbToHsl(rgb); // { h: 217, s: 0.91, l: 0.60, a: 1 }
const hex = hslToHex(hsl); // '#3B82F6'
```

---

## Default Colors for Semantic Use

```typescript
const SEMANTIC_COLORS = {
  primary: '#3B82F6',
  success: '#22C55E',
  warning: '#F59E0B',
  danger: '#EF4444',
  info: '#06B6D4',
  primaryLight: '#DBEAFE',
  successLight: '#DCFCE7',
  warningLight: '#FEF3C7',
  dangerLight: '#FEE2E2',
  infoLight: '#CFFAFE',
};
```

---

## Future Extensions

- [ ] Color harmony suggestions (complementary, triadic, etc.)
- [ ] Gradient picker
- [ ] Color blindness simulation
- [ ] WCAG contrast checker
- [ ] Palette import/export (JSON, ASE, GPL)
- [ ] Color history
- [ ] Eyedropper API integration