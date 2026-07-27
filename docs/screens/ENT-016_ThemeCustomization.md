# ENT-016: Theme Customization Screen Specification

**Module:** `features/theme/ThemeCustomizationPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
UI theme customization, color schemes, and branding configuration.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Theme Customization        │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ThemeCustomizationHeader (current theme)         │
│          ├──────────────────────────────────────────────────┤
│          │ ThemeCustomization (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ThemePreview (live preview)                 │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Colors] [Typography] [Layout]       │   │
│          │ │ [Branding]                                  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ColorPicker (color scheme)                  │   │
│          │ │ TypographySettings (fonts, sizes)           │   │
│          │ │ LayoutSettings (spacing, borders)           │   │
│          │ │ BrandingSettings (logo, name)               │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (theme suggestions, accessibility)                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ThemeCustomizationPage
├── ExecutiveHeader
├── Breadcrumb
├── ThemeCustomizationHeader
│   ├── Badge (current_theme)
│   └── Button (Reset to Default)
├── ThemeCustomization
│   ├── ThemePreview
│   │   ├── PreviewHeader
│   │   ├── PreviewSidebar
│   │   └── PreviewContent
│   ├── Tabs
│   │   ├── ColorsTab
│   │   │   └── ColorPicker
│   │   │       ├── PrimaryColor
│   │   │       ├── SecondaryColor
│   │   │       ├── BackgroundColor
│   │   │       ├── TextColor
│   │   │       └── AccentColor
│   │   ├── TypographyTab
│   │   │   └── TypographySettings
│   │   │       ├── Select (font_family)
│   │   │       ├── Input (font_size)
│   │   │       ├── Input (line_height)
│   │   │       └── Select (font_weight)
│   │   ├── LayoutTab
│   │   │   └── LayoutSettings
│   │   │       ├── Input (sidebar_width)
│   │   │       ├── Input (content_width)
│   │   │       ├── Input (border_radius)
│   │   │       └── Input (spacing)
│   │   └── BrandingTab
│   │       └── BrandingSettings
│   │           ├── ImageCropper (logo)
│   │           ├── Input (company_name)
│   │           ├── Input (tagline)
│   │           └── ColorPicker (brand_color)
│   └── ThemeActions
│       ├── Button (Save Theme)
│       ├── Button (Export Theme)
│       └── Button (Import Theme)
└── AiDock
    ├── AgentCard (Design Agent)
    └── EvidencePanel (theme suggestions)
```

## Data Sources

### Theme Settings
```typescript
// API: GET /api/v1/admin/theme
interface ThemeSettings {
  colors: ColorScheme;
  typography: TypographySettings;
  layout: LayoutSettings;
  branding: BrandingSettings;
}

interface ColorScheme {
  primary: string;
  secondary: string;
  background: string;
  text: string;
  accent: string;
}

interface TypographySettings {
  font_family: string;
  font_size: number;
  line_height: number;
  font_weight: number;
}

interface LayoutSettings {
  sidebar_width: number;
  content_width: number;
  border_radius: number;
  spacing: number;
}

interface BrandingSettings {
  logo_url?: string;
  company_name: string;
  tagline?: string;
  brand_color: string;
}
```

### React Query
```typescript
const { data: theme } = useQuery({
  queryKey: ['admin', 'theme'],
  queryFn: () => api.get('/api/v1/admin/theme'),
});

const saveTheme = useMutation({
  mutationFn: (request: ThemeSettings) => api.patch('/api/v1/admin/theme', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'theme'] });
    toast.success('Theme saved');
    applyTheme(theme);
  },
});
```

## Zustand Store
```typescript
// stores/themeCustomizationStore.ts
interface ThemeCustomizationState {
  activeTab: string;
  previewTheme: ThemeSettings;
  hasUnsavedChanges: boolean;
  setTab: (tab: string) => void;
  setPreviewTheme: (theme: ThemeSettings) => void;
  setUnsavedChanges: (hasChanges: boolean) => void;
}
```

## Interactions

### Change Color
1. Click color swatch
2. Open ColorPicker
3. Select new color
4. Update preview

### Update Typography
1. Select font family
2. Adjust sizes
3. Preview changes
4. Save when satisfied

### Modify Layout
1. Adjust sidebar width
2. Change border radius
3. Update spacing
4. Preview layout

### Update Branding
1. Upload logo
2. Enter company name
3. Set brand color
4. Save branding

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Preview + settings |
| Tablet (768-1024px) | Stacked preview/settings |
| Mobile (<768px) | Full-screen preview, bottom settings |

## Loading States
- Theme: Skeleton preview
- Settings: Skeleton form
- Preview: Loading indicator

## Error States
- Save failure: Toast error
- Upload failure: Retry button
- Network error: Toast notification

## Accessibility
- Color contrast checks
- Font size accessibility
- Screen reader: "Primary color: #3B82F6"
- Keyboard: Tab through settings

## Telemetry
- `theme_customization.view` — Screen loaded
- `theme_customization.color_change` — Color changed
- `theme_customization.save` — Theme saved
- `theme_customization.export` — Theme exported

## Implementation Notes
- Live preview of changes
- Color picker with presets
- Typography settings
- Branding configuration
- AiDock provides design suggestions
