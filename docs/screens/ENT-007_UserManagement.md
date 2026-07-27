# ENT-007: User Management Screen Specification

**Module:** `features/user-management/UserManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
User administration, profile management, role assignments, and access control.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > User Management            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ UserManagementHeader (user count, invite)        │
│          ├──────────────────────────────────────────────────┤
│          │ UserManagement (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Users] [Roles] [Groups] [Activity]  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ UserList (table with actions)               │   │
│          │ │ RoleList (role cards + permissions)         │   │
│          │ │ GroupList (group management)                │   │
│          │ │ ActivityLog (user actions)                  │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (user insights, permission suggestions)              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
UserManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── UserManagementHeader
│   ├── KpiStrip (user_count, active_count, pending_count)
│   └── Button (Invite User)
├── UserManagement
│   ├── Tabs
│   │   ├── UsersTab
│   │   │   └── UserList
│   │   │       └── Table<User>
│   │   │           ├── Avatar
│   │   │           ├── name
│   │   │           ├── email
│   │   │           ├── role
│   │   │           ├── status
│   │   │           └── actions (edit, remove)
│   │   ├── RolesTab
│   │   │   └── RoleList
│   │   │       └── RoleCard × N
│   │   │           ├── name
│   │   │           ├── permissions_count
│   │   │           └── Button (Edit)
│   │   ├── GroupsTab
│   │   │   └── GroupList
│   │   │       └── GroupCard × N
│   │   │           ├── name
│   │   │           ├── member_count
│   │   │           └── Button (Edit)
│   │   └── ActivityTab
│   │       └── ActivityLog
│   │           └── Table<UserActivity>
│   │               ├── user
│   │               ├── action
│   │               ├── timestamp
│   │               └── details
│   └── UserEditor
│       ├── Input (name)
│       ├── Input (email)
│       ├── Select (role)
│       ├── Select (group)
│       └── Button (Save)
└── AiDock
    ├── AgentCard (Admin Agent)
    └── EvidencePanel (user insights)
```

## Data Sources

### Users
```typescript
// API: GET /api/v1/admin/users
interface UserList {
  users: User[];
  total_count: number;
}

interface User {
  user_id: string;
  name: string;
  email: string;
  role: string;
  group: string;
  status: 'active' | 'inactive' | 'pending';
  last_active: string;
  created_at: string;
}
```

### Roles & Groups
```typescript
// API: GET /api/v1/admin/roles
interface RoleList {
  roles: Role[];
}

interface Role {
  role_id: string;
  name: string;
  description: string;
  permissions: Permission[];
  user_count: number;
}

// API: GET /api/v1/admin/groups
interface GroupList {
  groups: Group[];
}

interface Group {
  group_id: string;
  name: string;
  description: string;
  member_count: number;
}
```

### React Query
```typescript
const { data: users } = useQuery({
  queryKey: ['admin', 'users', filters],
  queryFn: () => api.get('/api/v1/admin/users', { params: filters }),
});

const { data: roles } = useQuery({
  queryKey: ['admin', 'roles'],
  queryFn: () => api.get('/api/v1/admin/roles'),
});

const { data: groups } = useQuery({
  queryKey: ['admin', 'groups'],
  queryFn: () => api.get('/api/v1/admin/groups'),
});

const inviteUser = useMutation({
  mutationFn: (request: InviteUserRequest) => api.post('/api/v1/admin/users/invite', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    toast.success('Invitation sent');
  },
});

const updateUser = useMutation({
  mutationFn: ({ userId, request }: { userId: string; request: UpdateUserRequest }) =>
    api.patch(`/api/v1/admin/users/${userId}`, request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    toast.success('User updated');
  },
});
```

## Zustand Store
```typescript
// stores/userManagementStore.ts
interface UserManagementState {
  activeTab: string;
  selectedUser: string | null;
  setTab: (tab: string) => void;
  setUser: (id: string | null) => void;
}
```

## Interactions

### Invite User
1. Click "Invite User"
2. Open InviteModal
3. Enter email/role
4. Send invitation

### Edit User
1. Click user row
2. Open UserEditor
3. Modify fields
4. Save changes

### Manage Roles
1. Click Roles tab
2. Edit role permissions
3. Save role
4. Update users

### View Activity
1. Click Activity tab
2. Filter by user/action
3. View details
4. Export log

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with tables |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Users: Skeleton table
- Roles: Skeleton cards
- Groups: Skeleton cards
- Activity: Skeleton table

## Error States
- Invite failure: Toast error
- Update failure: Rollback changes
- Network error: Retry button

## Accessibility
- Table rows are focusable
- Changes announced via `aria-live`
- Screen reader: "User X, role Y"
- Keyboard: Enter to edit, Delete to remove

## Telemetry
- `user_management.view` — Screen loaded
- `user_management.invite` — User invited
- `user_management.update` — User updated
- `user_management.remove` — User removed

## Implementation Notes
- 4 tabs for different aspects
- UserList with sortable table
- RoleList for permission management
- GroupList for group management
- ActivityLog for audit trail
