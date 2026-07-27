# ENT-002: Team Management Screen Specification

**Module:** `features/team/TeamPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Team member management, role assignments, permissions configuration, and activity monitoring.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Team Management            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TeamHeader (member count, invite button)         │
│          ├──────────────────────────────────────────────────┤
│          │ TeamManagement (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Members] [Roles] [Activity]         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ MembersList (table with actions)            │   │
│          │ │ RoleManagement (role cards + permissions)   │   │
│          │ │ ActivityLog (recent team actions)           │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (team insights, permission suggestions)              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TeamPage
├── ExecutiveHeader
├── Breadcrumb
├── TeamHeader
│   ├── KpiStrip (member_count, active_count, pending_invites)
│   └── Button (Invite Member)
├── TeamManagement
│   ├── Tabs
│   │   ├── MembersTab
│   │   │   └── Table<TeamMember>
│   │   │       ├── Avatar
│   │   │       ├── name
│   │   │       ├── email
│   │   │       ├── role
│   │   │       ├── status
│   │   │       └── actions (edit, remove)
│   │   ├── RolesTab
│   │   │   └── RoleList
│   │   │       └── RoleCard × N
│   │   │           ├── role_name
│   │   │           ├── permissions_count
│   │   │           └── Button (Edit)
│   │   └── ActivityTab
│   │       └── ActivityTimeline
│   │           └── ActivityItem × N
│   └── InviteModal
│       ├── Input (email)
│       ├── Select (role)
│       └── Button (Send Invite)
└── AiDock
    ├── AgentCard (Admin Agent)
    └── EvidencePanel (team insights)
```

## Data Sources

### Team Members
```typescript
// API: GET /api/v1/admin/users
interface TeamMemberList {
  members: TeamMember[];
  total_count: number;
}

interface TeamMember {
  user_id: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive' | 'pending';
  last_active: string;
  created_at: string;
}
```

### Roles & Permissions
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
  member_count: number;
}

interface Permission {
  permission_id: string;
  resource: string;
  action: string;
  description: string;
}
```

### Team Activity
```typescript
// API: GET /api/v1/admin/activity
interface TeamActivity {
  activities: ActivityItem[];
}

interface ActivityItem {
  activity_id: string;
  user_id: string;
  user_name: string;
  action: string;
  resource: string;
  timestamp: string;
  details?: string;
}
```

### React Query
```typescript
const { data: members } = useQuery({
  queryKey: ['admin', 'users'],
  queryFn: () => api.get('/api/v1/admin/users'),
});

const { data: roles } = useQuery({
  queryKey: ['admin', 'roles'],
  queryFn: () => api.get('/api/v1/admin/roles'),
});

const { data: activity } = useQuery({
  queryKey: ['admin', 'activity'],
  queryFn: () => api.get('/api/v1/admin/activity'),
});

const inviteMember = useMutation({
  mutationFn: (request: { email: string; role: string }) =>
    api.post('/api/v1/admin/users/invite', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    toast.success('Invitation sent');
  },
});

const updateRole = useMutation({
  mutationFn: ({ roleId, permissions }: { roleId: string; permissions: string[] }) =>
    api.patch(`/api/v1/admin/roles/${roleId}`, { permissions }),
});
```

## Zustand Store
```typescript
// stores/teamStore.ts
interface TeamState {
  activeTab: 'members' | 'roles' | 'activity';
  selectedMember: string | null;
  selectedRole: string | null;
  setTab: (tab: string) => void;
  setMember: (id: string | null) => void;
  setRole: (id: string | null) => void;
}
```

## Interactions

### Invite Member
1. Click "Invite Member" button
2. Open InviteModal
3. Enter email and role
4. Send invite
5. Refresh member list

### Edit Member
1. Click member row
2. Open EditDrawer
3. Change role/status
4. Save changes
5. Update member list

### Edit Role
1. Click role card
2. Open RoleEditor
3. Toggle permissions
4. Save role
5. Update permissions

### View Activity
1. Click Activity tab
2. View recent actions
3. Click activity for details
4. Filter by user/action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with table |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | List view, bottom details |

## Loading States
- Members: Skeleton table rows
- Roles: Skeleton cards
- Activity: Skeleton timeline

## Error States
- Invite failure: Toast error
- Permission error: Warning message
- Network error: Retry button

## Accessibility
- Table rows are focusable
- Role changes announced via `aria-live`
- Screen reader: "Member X, role Y"
- Keyboard: Enter to select, Delete to remove

## Telemetry
- `team.view` — Screen loaded
- `team.invite` — Member invited
- `team.role_change` — Role updated
- `team.remove` — Member removed

## Implementation Notes
- MembersTab shows table with actions
- RolesTab for permission management
- ActivityTab logs team actions
- AiDock provides team insights
- InviteModal for adding members
