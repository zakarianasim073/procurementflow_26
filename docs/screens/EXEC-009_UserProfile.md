# EXEC-009: User Profile Screen Specification

**Module:** `features/user-profile/UserProfilePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
User profile management, preferences, and account settings.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > User Profile               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ UserProfileHeader (user info, status)            │
│          ├──────────────────────────────────────────────────┤
│          │ UserProfile (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Avatar (profile picture)                    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Profile] [Security] [Preferences]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ProfileForm (basic info)                    │   │
│          │ │ SecuritySettings (password, 2FA)            │   │
│          │ │ PreferencesForm (notifications, theme)      │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (profile insights, recommendations)                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
UserProfilePage
├── ExecutiveHeader
├── Breadcrumb
├── UserProfileHeader
│   ├── Avatar (large)
│   ├── KpiCard (name)
│   ├── KpiCard (email)
│   └── KpiCard (role)
├── UserProfile
│   ├── Avatar
│   │   └── ImageCropper (upload/edit)
│   ├── Tabs
│   │   ├── ProfileTab
│   │   │   └── ProfileForm
│   │   │       ├── Input (name)
│   │   │       ├── Input (email)
│   │   │       ├── Input (phone)
│   │   │       ├── Textarea (bio)
│   │   │       └── Button (Save)
│   │   ├── SecurityTab
│   │   │   └── SecuritySettings
│   │   │       ├── Button (Change Password)
│   │   │       ├── Switch (2FA)
│   │   │       ├── Table<Session>
│   │   │       │   ├── device
│   │   │       │   ├── ip_address
│   │   │       │   └── last_active
│   │   │       └── Button (Revoke All)
│   │   └── PreferencesTab
│   │       └── PreferencesForm
│   │           ├── Switch (email_notifications)
│   │           ├── Switch (push_notifications)
│   │           ├── Select (theme)
│   │           ├── Select (language)
│   │           └── Button (Save)
│   └── ProfileActions
│       ├── Button (Export Data)
│       └── Button (Delete Account)
└── AiDock
    ├── AgentCard (Admin Agent)
    └── EvidencePanel (profile insights)
```

## Data Sources

### User Profile
```typescript
// API: GET /api/v1/auth/me
interface UserProfile {
  user_id: string;
  name: string;
  email: string;
  phone?: string;
  bio?: string;
  avatar_url?: string;
  role: string;
  created_at: string;
  last_login: string;
}

// API: PATCH /api/v1/auth/me
interface UpdateProfileRequest {
  name?: string;
  email?: string;
  phone?: string;
  bio?: string;
  avatar?: File;
}
```

### Sessions
```typescript
// API: GET /api/v1/auth/sessions
interface SessionList {
  sessions: Session[];
}

interface Session {
  session_id: string;
  device: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
  last_active: string;
  current: boolean;
}
```

### React Query
```typescript
const { data: profile } = useQuery({
  queryKey: ['auth', 'me'],
  queryFn: () => api.get('/api/v1/auth/me'),
});

const { data: sessions } = useQuery({
  queryKey: ['auth', 'sessions'],
  queryFn: () => api.get('/api/v1/auth/sessions'),
});

const updateProfile = useMutation({
  mutationFn: (request: UpdateProfileRequest) => api.patch('/api/v1/auth/me', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
    toast.success('Profile updated');
  },
});

const revokeSession = useMutation({
  mutationFn: (sessionId: string) => api.delete(`/api/v1/auth/sessions/${sessionId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['auth', 'sessions'] });
    toast.success('Session revoked');
  },
});
```

## Zustand Store
```typescript
// stores/userProfileStore.ts
interface UserProfileState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### Edit Profile
1. Click Profile tab
2. Edit fields
3. Save changes
4. Update header

### Change Password
1. Click Security tab
2. Click "Change Password"
3. Enter old/new password
4. Submit change

### Manage Sessions
1. Click Security tab
2. View session list
3. Revoke session
4. Update list

### Update Preferences
1. Click Preferences tab
2. Toggle settings
3. Save changes
4. Apply theme

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with forms |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Profile: Skeleton form
- Sessions: Skeleton table
- Preferences: Skeleton form

## Error States
- Update failure: Toast error
- Password failure: Validation message
- Network error: Retry button

## Accessibility
- Form fields are focusable
- Changes announced via `aria-live`
- Screen reader: "Profile updated"
- Keyboard: Tab through fields, Enter to save

## Telemetry
- `user_profile.view` — Screen loaded
- `user_profile.update` — Profile updated
- `user_profile.password_change` — Password changed
- `user_profile.session_revoke` — Session revoked

## Implementation Notes
- Profile editing with avatar
- Security settings with 2FA
- Session management
- AiDock provides profile insights
- Export for data portability
