# ENT-017: Localization Screen Specification

**Module:** `features/localization/LocalizationPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Multi-language support, translation management, and locale configuration.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Localization               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ LocalizationHeader (current locale, progress)    │
│          ├──────────────────────────────────────────────────┤
│          │ Localization (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Languages] [Translations] [Settings] │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ LanguageList (available languages)          │   │
│          │ │ TranslationEditor (key-value pairs)         │   │
│          │ │ LocaleSettings (formatting)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (translation insights, suggestions)                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
LocalizationPage
├── ExecutiveHeader
├── Breadcrumb
├── LocalizationHeader
│   ├── Badge (current_locale)
│   ├── Progress (translation_completion)
│   └── Button (Add Language)
├── Localization
│   ├── Tabs
│   │   ├── LanguagesTab
│   │   │   └── LanguageList
│   │   │       └── LanguageCard × N
│   │   │           ├── flag
│   │   │           ├── name
│   │   │           ├── native_name
│   │   │           ├── completion_pct
│   │   │           └── actions (set_default, delete)
│   │   ├── TranslationsTab
│   │   │   └── TranslationEditor
│   │   │       ├── SearchBar (key search)
│   │   │       ├── FilterBar (status)
│   │   │       └── Table<Translation>
│   │   │           ├── key
│   │   │           ├── source_text
│   │   │           ├── translated_text
│   │   │           ├── status
│   │   │           └── Button (Edit)
│   │   └── SettingsTab
│   │       └── LocaleSettings
│   │           ├── Select (date_format)
│   │           ├── Select (time_format)
│   │           ├── Select (number_format)
│   │           ├── Select (currency)
│   │           └── Button (Save)
│   └── TranslationStats
│       ├── KpiCard (total_keys)
│       ├── KpiCard (translated)
│       └── KpiCard (pending)
└── AiDock
    ├── AgentCard (Translation Agent)
    └── EvidencePanel (translation insights)
```

## Data Sources

### Languages
```typescript
// API: GET /api/v1/admin/localization/languages
interface LanguageList {
  languages: Language[];
}

interface Language {
  language_id: string;
  code: string;
  name: string;
  native_name: string;
  flag: string;
  completion_pct: number;
  is_default: boolean;
  is_enabled: boolean;
}
```

### Translations
```typescript
// API: GET /api/v1/admin/localization/translations
interface TranslationList {
  translations: Translation[];
  total_count: number;
}

interface Translation {
  translation_id: string;
  key: string;
  source_text: string;
  translated_text: string;
  status: 'translated' | 'pending' | 'outdated';
  updated_at: string;
}
```

### React Query
```typescript
const { data: languages } = useQuery({
  queryKey: ['admin', 'localization', 'languages'],
  queryFn: () => api.get('/api/v1/admin/localization/languages'),
});

const { data: translations } = useQuery({
  queryKey: ['admin', 'localization', 'translations', filters],
  queryFn: () => api.get('/api/v1/admin/localization/translations', { params: filters }),
});

const updateTranslation = useMutation({
  mutationFn: ({ translationId, text }: { translationId: string; text: string }) =>
    api.patch(`/api/v1/admin/localization/translations/${translationId}`, { translated_text: text }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'localization'] });
    toast.success('Translation updated');
  },
});

const addLanguage = useMutation({
  mutationFn: (request: AddLanguageRequest) => api.post('/api/v1/admin/localization/languages', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'localization'] });
    toast.success('Language added');
  },
});
```

## Zustand Store
```typescript
// stores/localizationStore.ts
interface LocalizationState {
  activeTab: string;
  selectedLanguage: string | null;
  setTab: (tab: string) => void;
  setLanguage: (id: string | null) => void;
}
```

## Interactions

### View Languages
1. Click Languages tab
2. View language list
3. Check completion
4. Manage languages

### Edit Translation
1. Click translation row
2. Open TranslationEditor
3. Enter translated text
4. Save changes

### Set Default Language
1. Click Set Default button
2. Confirm change
3. Update default
4. Refresh UI

### Configure Locale
1. Click Settings tab
2. Edit formatting
3. Save changes
4. Apply locale

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with tables |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Languages: Skeleton cards
- Translations: Skeleton table
- Settings: Skeleton form

## Error States
- Update failure: Toast error
- Add failure: Toast error
- Network error: Toast notification

## Accessibility
- Languages are focusable
- Progress announced via `aria-live`
- Screen reader: "English, 85% translated"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `localization.view` — Screen loaded
- `localization.language_add` — Language added
- `localization.translation_update` — Translation updated
- `localization.default_change` — Default changed

## Implementation Notes
- Language management with CRUD
- Translation editor with search
- Locale formatting settings
- AiDock provides translation insights
- Export for offline translation
