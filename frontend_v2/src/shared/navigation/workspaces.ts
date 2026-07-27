/**
 * Canonical workspace/section nav model. See docs/frontend/07_NAVIGATION.md and
 * docs/frontend/02_INFORMATION_ARCHITECTURE.md for the page-by-page mapping this implements.
 */

export interface WorkspaceSection {
  id: string
  label: string
  path: string
  /** If set, WorkspaceNav hides this section unless useWorkspacePermissions grants it. */
  requiresPermission?: string
}

export interface Workspace {
  id: string
  label: string
  path: string
  /** lucide-react icon name, resolved by WorkspaceSwitcher (kept as a string to avoid an icon-lib dependency here). */
  icon: string
  sections: WorkspaceSection[]
}

export const WORKSPACES: Workspace[] = [
  {
    id: 'executive',
    label: 'Executive',
    path: '/executive',
    icon: 'LayoutDashboard',
    sections: [
      { id: 'overview', label: 'Overview', path: '/executive' },
      { id: 'pipeline', label: 'Pipeline', path: '/executive/pipeline' },
    ],
  },
  {
    id: 'opportunity',
    label: 'Opportunity Intelligence',
    path: '/opportunity',
    icon: 'Radar',
    sections: [
      { id: 'discovery', label: 'Discovery', path: '/opportunity/discovery' },
      { id: 'qualification', label: 'Qualification', path: '/opportunity/qualification' },
      { id: 'monitoring', label: 'Monitoring', path: '/opportunity/monitoring' },
    ],
  },
  {
    id: 'tender',
    label: 'Tender',
    path: '/tender',
    icon: 'FileText',
    sections: [
      { id: 'overview', label: 'Tender List', path: '/tender' },
      { id: 'boq', label: 'BOQ', path: '/tender/boq' },
      { id: 'pricing', label: 'Pricing', path: '/tender/pricing' },
      { id: 'compliance', label: 'Compliance', path: '/tender/compliance' },
      { id: 'competitors', label: 'Competitors', path: '/tender/competitors' },
      { id: 'submission', label: 'Submission', path: '/tender/submission' },
      { id: 'award', label: 'Award', path: '/tender/award' },
    ],
  },
  {
    id: 'trust',
    label: 'Trust Platform',
    path: '/trust',
    icon: 'ShieldCheck',
    sections: [
      { id: 'chat', label: 'AI Chat', path: '/trust/chat' },
      { id: 'agents', label: 'Agent Activity', path: '/trust/agents' },
    ],
  },
  {
    id: 'knowledge',
    label: 'Knowledge Platform',
    path: '/knowledge',
    icon: 'BookOpen',
    sections: [
      { id: 'market', label: 'Market Research', path: '/knowledge/market' },
      { id: 'documents', label: 'Document Knowledge', path: '/knowledge/documents' },
      { id: 'intelligence', label: 'Intelligence Explorer', path: '/knowledge/intelligence' },
      { id: 'sor', label: 'SOR Rates', path: '/knowledge/sor' },
      { id: 'analytics', label: 'Market Analytics', path: '/knowledge/analytics' },
      { id: 'analytics-dashboard', label: 'Analytics Dashboard', path: '/knowledge/analytics-dashboard' },
      { id: 'feedback', label: 'Feedback Analytics', path: '/knowledge/feedback' },
      { id: 'clauses', label: 'Clause Explorer', path: '/knowledge/clauses' },
      { id: 'rule-graph', label: 'Rule Graph', path: '/knowledge/rule-graph' },
      { id: 'ppr2025', label: 'PPR 2025', path: '/knowledge/ppr2025' },
      { id: 'document-tools', label: 'Document Tools', path: '/knowledge/document-tools' },
      { id: 'learning', label: 'Learning Hub', path: '/knowledge/learning' },
      { id: 'search', label: 'Search', path: '/knowledge/search' },
    ],
  },
  {
    id: 'enterprise',
    label: 'Enterprise',
    path: '/enterprise',
    icon: 'Building2',
    sections: [
      { id: 'clients', label: 'Clients', path: '/enterprise/clients' },
      { id: 'team', label: 'Team', path: '/enterprise/team' },
      { id: 'settings', label: 'Settings', path: '/enterprise/settings' },
      { id: 'audit', label: 'Audit Log', path: '/enterprise/audit', requiresPermission: 'enterprise:admin' },
      { id: 'roi', label: 'ROI Dashboard', path: '/enterprise/roi' },
      { id: 'rbac', label: 'Roles & Permissions', path: '/enterprise/rbac', requiresPermission: 'enterprise:admin' },
    ],
  },
  {
    id: 'management',
    label: 'Management',
    path: '/management',
    icon: 'Settings',
    sections: [
      { id: 'documents', label: 'Documents', path: '/documents' },
      { id: 'team', label: 'Team Members', path: '/team' },
      { id: 'settings', label: 'User Settings', path: '/settings' },
      { id: 'admin', label: 'Admin Dashboard', path: '/admin/dashboard', requiresPermission: 'enterprise:admin' },
      { id: 'agents', label: 'Agent Administration', path: '/admin/agents', requiresPermission: 'enterprise:admin' },
    ],
  },
]

export function findWorkspaceForPath(pathname: string): Workspace {
  return (
    WORKSPACES.find((workspace) => pathname.startsWith(workspace.path))
    ?? WORKSPACES.find((workspace) =>
      workspace.sections.some((section) =>
        pathname === section.path || pathname.startsWith(`${section.path}/`),
      ),
    )
    ?? WORKSPACES[0]
  )
}
