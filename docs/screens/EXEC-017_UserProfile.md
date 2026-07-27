# EXEC-017: User Profile Screen Specification

**Module:** `features/user-profile/UserProfilePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
User profile management, preferences, and account settings.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > User Profile              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ UserProfileHeader (user, role)                   │
│          ├──────────────────────────────────────────────────┤
│          │ UserProfile (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Profile] [Settings] [Security]       │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ProfileTab (user info)                      │   │
│          │ │ SettingsTab (preferences)                   │   │
│          │ │ SecurityTab (security settings)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (personalization suggestions)                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
UserProfilePage
├── ExecutiveHeader
├── Breadcrumb
├── UserProfileHeader
│   ├── Avatar (user_avatar)
│   ├── user_info (name, email, role)
│   └── Button (Edit Profile)
├── UserProfile
│   ├── Tabs
│   │   ├── ProfileTab
│   │   │   ├── AvatarUpload
│   │   │   ├── PersonalInfoForm
│   │   │   │   ├── name
│   │   │   │   ├── email
│   │   │   │   ├── phone
│   │   │   │   └── department
│   │   │   └── BioSection
│   │   ├── SettingsTab
│   │   │   ├── NotificationPreferences
│   │   │   ├── DisplayPreferences
│   │   │   │   ├── theme
│   │   │   │   ├── language
│   │   │   │   └── timezone
│   │   │   └── CommunicationPreferences
│   │   └── SecurityTab
│   │       ├── PasswordChange
│   │       ├── TwoFactorAuth
│   │       ├── ActiveSessions
│   │       └── LoginHistory
│   └── ActivityLog
│       └── ActivityEntry × N
│           ├── timestamp
│           ├── action
│           └── details
└── AiDock
    ├── AgentCard (Personalization Agent)
    └── EvidencePanel (profile insights)
```

## Data Sources

### User Profile
```typescript
// API: GET /api/v1/auth/profile
interface UserProfile {
  user_id: string;
  name: string;
  email: string;
  phone?: string;
  department?: string;
  role: string;
  avatar_url?: string;
  bio?: string;
  preferences: UserPreferences;
  created_at: string;
  last_login: string;
}

interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  notifications: NotificationPreferences;
}

interface NotificationPreferences {
  email: boolean;
  push: boolean;
  in_app: boolean;
}
```

### React Query
```typescript
const { data: profile } = useQuery({
  queryKey: ['auth', 'profile'],
  queryFn: () => api.get('/api/v1/auth/profile'),
});

const updateProfile = useMutation({
  mutationFn: (updates: UpdateProfileRequest) => api.patch('/api/v1/auth/profile', updates),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['auth', 'profile'] });
    toast.success('Profile updated');
  },
});

const changePassword = useMutation({
  mutationFn: (passwords: ChangePasswordRequest) => api.post('/api/v1/auth/change-password', passwords),
  onSuccess: () => {
    toast.success('Password changed');
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
1. Click Edit button
2. Modify fields
3. Save changes
4. Update display

### Change Avatar
1. Click avatar
2. Upload image
3. Crop image
4. Save avatar

### Update Preferences
1. Click Settings tab
2. Modify preferences
3. Save changes
4. Apply changes

### Change Password
1. Click Security tab
2. Enter current password
3. Enter new password
4. Confirm change

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Profile: Loading form
- Avatar: Uploading image
- Password: Loading state

## Error States
- Update failure: Toast error
- Password failure: Toast error
- Network error: Toast notification

## Accessibility
- Form fields are focusable
- Updates announced via `aria-live`
- Screen reader: "Profile updated successfully"
- Keyboard: Tab through fields

## Telemetry
- `user_profile.view` — Screen loaded
- `user_profile.update` — Profile updated
- `user_profile.avatar_change` — Avatar changed
- `user_profile.password_change` — Password changed

## Implementation Notes
- Profile management
- Avatar upload/crop
- Preference settings
- AiDock provides personalization
- Security controls
