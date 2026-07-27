# ENT-030: User Management Screen Specification

**Module:** `features/user-management/UserManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Manage users, roles, permissions, and access control.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > User Management            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ UserManagementHeader (users, roles)              │
│          ├──────────────────────────────────────────────────┤
│          │ UserManagement (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Users] [Roles] [Permissions]         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ UsersTab (user list)                        │   │
│          │ │ RolesTab (role management)                  │   │
│          │ │ PermissionsTab (permission settings)        │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (user insights)                                      │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
UserManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── UserManagementHeader
│   ├── KpiStrip (user_count, active_count, role_count)
│   └── Button (Add User)
├── UserManagement
│   ├── Tabs
│   │   ├── UsersTab
│   │   │   └── UserList
│   │   │       └── UserCard × N
│   │   │           ├── name
│   │   │           ├── email
│   │   │           ├── role
│   │   │           ├── status
│   │   │           └── actions (edit, disable, delete)
│   │   ├── RolesTab
│   │   │   └── RoleList
│   │   │       └── RoleCard × N
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── permissions_count
│   │   │           └── actions (edit, delete)
│   │   └── PermissionsTab
│   │       └── PermissionMatrix
│   │           └── Permission × N
│   │               ├── resource
│   │               ├── actions
│   │               └── roles
│   ├── UserDetails
│   │   ├── user_info
│   │   ├── activity_log
│   │   └── permissions
│   └── UserStats
│       ├── chart (users_by_role)
│       ├── chart (active_users)
│       └── chart (login_frequency)
└── AiDock
    ├── AgentCard (User Agent)
    └── EvidencePanel (user insights)
```

## Data Sources

### Users
```typescript
// API: GET /api/v1/admin/users
interface UserList {
  users: User[];
  total_count: number;
  active_count: number;
}

interface User {
  user_id: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive' | 'suspended';
  last_login: string;
  created_at: string;
}

interface Role {
  role_id: string;
  name: string;
  description: string;
  permissions: string[];
  users_count: number;
}

interface Permission {
  permission_id: string;
  resource: string;
  actions: string[];
  roles: string[];
}
```

### React Query
```typescript
const { data: users } = useQuery({
  queryKey: ['admin', 'users'],
  queryFn: () => api.get('/api/v1/admin/users'),
});

const createUser = useMutation({
  mutationFn: (user: CreateUserRequest) => api.post('/api/v1/admin/users', user),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    toast.success('User created');
  },
});

const updateUser = useMutation({
  mutationFn: ({ userId, updates }: { userId: string; updates: UpdateUserRequest }) =>
    api.patch(`/api/v1/admin/users/${userId}`, updates),
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
  setTab: (tab: string) => void;
}
```

## Interactions

### View Users
1. Click Users tab
2. View user list
3. Check details
4. Manage user

### Manage Roles
1. Click Roles tab
2. View role list
3. Edit permissions
4. Assign users

### Set Permissions
1. Click Permissions tab
2. View matrix
3. Adjust permissions
4. Save changes

### Add User
1. Click Add User
2. Fill form
3. Assign role
4. Save user

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified list |

## Loading States
- Users: Skeleton cards
- Roles: Loading list
- Permissions: Loading matrix

## Error States
- Create failure: Toast error
- Update failure: Toast error
- Network error: Toast notification

## Accessibility
- Users are focusable
- Status announced via `aria-live`
- Screen reader: "User: John Doe, role: Admin"
- Keyboard: Tab through users

## Telemetry
- `user_management.view` — Screen loaded
- `user_management.create` — User created
- `user_management.update` — User updated
- `user_management.role_edit` — Role edited

## Implementation Notes
- User management
- Role-based access control
- Permission matrix
- AiDock provides user insights
- Audit trail
