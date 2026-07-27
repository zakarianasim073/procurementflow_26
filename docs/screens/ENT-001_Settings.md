# ENT-001: Settings Screen Specification

**Module:** `features/settings/SettingsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
User preferences, system configuration, notification settings, and account management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings                              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SettingsSidebar (navigation)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Profile                                     │   │
│          │ │ Notifications                               │   │
│          │ │ Appearance                                  │   │
│          │ │ Integrations                                │   │
│          │ │ Security                                    │   │
│          │ │ Billing                                     │   │
│          │ └────────────────────────────────────────────┘   │
│          ├──────────────────────────────────────────────────┤
│          │ SettingsContent (main area)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Current Section Content                    │   │
│          │ │ (varies by selection)                      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ [Save Changes] [Reset to Default]          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ TrustPanel (system status, version info)                    │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SettingsPage
├── ExecutiveHeader
├── Breadcrumb
├── SettingsSidebar
│   └── NavigationItem × N
│       ├── icon
│       ├── label
│       └── badge (if pending changes)
├── SettingsContent
│   ├── ProfileSection
│   │   ├── Avatar
│   │   ├── Input (name)
│   │   ├── Input (email)
│   │   ├── Select (role)
│   │   └── Button (Change Password)
│   ├── NotificationsSection
│   │   ├── Switch (email notifications)
│   │   ├── Switch (push notifications)
│   │   ├── Switch (SMS notifications)
│   │   └── NotificationPreferences (per type)
│   ├── AppearanceSection
│   │   ├── Select (theme: light/dark/system)
│   │   ├── Select (language)
│   │   ├── Select (timezone)
│   │   └── ColorPicker (accent color)
│   ├── IntegrationsSection
│   │   ├── IntegrationCard × N
│   │   │   ├── Avatar (service logo)
│   │   │   ├── Badge (status)
│   │   │   └── Button (Connect/Disconnect)
│   │   └── Button (Add Integration)
│   ├── SecuritySection
│   │   ├── Switch (2FA)
│   │   ├── Button (Change Password)
│   │   ├── Button (Active Sessions)
│   │   └── Button (Delete Account)
│   └── BillingSection
│       ├── SubscriptionCard
│       ├── UsageMetrics
│       └── Button (Manage Billing)
└── TrustPanel
```

## Data Sources

### User Profile
```typescript
// API: GET /api/v1/auth/me
interface UserProfile {
  user_id: string;
  name: string;
  email: string;
  role: string;
  avatar_url?: string;
  created_at: string;
  last_login: string;
}

// API: PATCH /api/v1/auth/me
interface UpdateProfileRequest {
  name?: string;
  email?: string;
  avatar?: File;
}
```

### Notification Settings
```typescript
// API: GET /api/v1/notifications/preferences
interface NotificationPreferences {
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  preferences: {
    type: string;
    email: boolean;
    push: boolean;
    sms: boolean;
  }[];
}

// API: PATCH /api/v1/notifications/preferences
interface UpdatePreferencesRequest {
  email_enabled?: boolean;
  push_enabled?: boolean;
  sms_enabled?: boolean;
  preferences?: Record<string, { email: boolean; push: boolean; sms: boolean }>;
}
```

### React Query
```typescript
const { data: profile } = useQuery({
  queryKey: ['auth', 'me'],
  queryFn: () => api.get('/api/v1/auth/me'),
});

const { data: preferences } = useQuery({
  queryKey: ['notifications', 'preferences'],
  queryFn: () => api.get('/api/v1/notifications/preferences'),
});

const updateProfile = useMutation({
  mutationFn: (request: UpdateProfileRequest) => api.patch('/api/v1/auth/me', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
    toast.success('Profile updated');
  },
});

const updatePreferences = useMutation({
  mutationFn: (request: UpdatePreferencesRequest) =>
    api.patch('/api/v1/notifications/preferences', request),
});
```

## Zustand Store
```typescript
// stores/settingsStore.ts
interface SettingsState {
  activeSection: string;
  hasUnsavedChanges: boolean;
  setSection: (section: string) => void;
  setUnsavedChanges: (hasChanges: boolean) => void;
}
```

## Interactions

### Section Navigation
1. Click sidebar item
2. Update URL: `/settings?section=profile`
3. Preserve unsaved changes prompt
4. Load section content

### Profile Update
1. Edit fields
2. Auto-save on blur
3. Show success toast
4. Update header avatar

### Notification Toggle
1. Toggle switch
2. Auto-save preference
3. Update notification system
4. Show confirmation

### Theme Change
1. Select theme option
2. Apply theme immediately
3. Save preference
4. Update CSS variables

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Sidebar + content |
| Tablet (768-1024px) | Top tabs + content |
| Mobile (<768px) | Full-screen sections |

## Loading States
- Profile: Skeleton form
- Preferences: Skeleton switches
- Integrations: Skeleton cards

## Error States
- Save failure: Toast error
- Validation error: Inline messages
- Network error: Retry button

## Accessibility
- Sidebar items are focusable
- Section changes announced via `aria-live`
- Screen reader: "Section: Profile"
- Keyboard: Enter to select, Arrow keys to navigate

## Telemetry
- `settings.view` — Screen loaded
- `settings.section_change` — Section navigated
- `settings.save` — Changes saved
- `settings.theme_change` — Theme changed

## Implementation Notes
- Sidebar navigation for sections
- Auto-save for most settings
- Confirmation for destructive actions
- TrustPanel shows system info
- Unsaved changes warning on navigation
