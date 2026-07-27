import { useNavigate, useLocation } from 'react-router-dom'
import { Users, Settings, Shield, Building2, Activity } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@shared/ui/Tabs'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { useTenantInfo, useTeamMembers, useRoles, useAuditLogs } from '@hooks/index'

const TABS = [
  { id: 'clients', label: 'Clients', icon: Building2 },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'rbac', label: 'Roles', icon: Shield },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'audit', label: 'Audit Log', icon: Activity },
] as const

type TabId = typeof TABS[number]['id']

function tabFromPath(path: string): TabId {
  if (path.includes('/team')) return 'team'
  if (path.includes('/rbac') || path.includes('/roles')) return 'rbac'
  if (path.includes('/settings')) return 'settings'
  if (path.includes('/audit')) return 'audit'
  return 'clients'
}

function pathForTab(tab: TabId): string {
  if (tab === 'team') return '/enterprise/team'
  if (tab === 'rbac') return '/enterprise/rbac'
  if (tab === 'settings') return '/enterprise/settings'
  if (tab === 'audit') return '/enterprise/audit'
  return '/enterprise/clients'
}

function ClientsPanel() {
  const tenant = useTenantInfo()

  if (tenant.isLoading) return <Skeleton className="h-40 w-full rounded-xl" />

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Client No. {tenant.data?.config?.client_rank || 1}</h2>
        {tenant.data ? (
          <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Name</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white">{tenant.data.name}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Plan</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white capitalize">{tenant.data.plan}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Slug</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white">{tenant.data.slug}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Dossier</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white">{Number(tenant.data.config?.documents_uploaded || 0)} documents</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Verified average turnover</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white">৳{(Number(tenant.data.config?.annual_turnover_bdt || 0) / 1e7).toFixed(2)} Cr</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Key personnel</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white">{Number(tenant.data.config?.key_personnel_verified_count || 0)} verified</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Equipment register</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white">{tenant.data.config?.equipment_register_verified ? 'Verified' : 'Pending'}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Works scope</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white">{tenant.data.config?.procurement_scope || 'Works'}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">Primary email</p>
              <p className="mt-0.5 truncate text-sm font-medium text-gray-900 dark:text-white">{tenant.data.config?.primary_email || tenant.data.config?.email || 'Not provided'}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <p className="text-xs text-gray-500">BWDB similar-work capacity</p>
              <p className="mt-0.5 text-sm font-medium text-gray-900 dark:text-white">৳{(Number(tenant.data.config?.bwdb_similar_work_max_bdt || 0) / 1e7).toFixed(2)} Cr</p>
            </div>
          </div>
          {Boolean(tenant.data.config?.compliance_alerts?.length) && <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <p className="text-sm font-semibold text-amber-900">Compliance renewals required</p>
            <ul className="mt-2 grid gap-1 md:grid-cols-2">{(tenant.data.config?.compliance_alerts || []).map((alert: string) => <li key={alert} className="text-xs text-amber-800">• {alert}</li>)}</ul>
          </div>}
          </>
        ) : (
          <EmptyState title="No tenant data" description="Tenant information could not be loaded." />
        )}
      </div>
    </div>
  )
}

function TeamPanel() {
  const members = useTeamMembers()

  if (members.isLoading) return <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}</div>

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Team Members</h2>
        {members.data && members.data.length > 0 ? (
          <div className="space-y-2">
            {members.data.map(m => (
              <div key={m.id} className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{m.name || m.email}</p>
                  <p className="text-xs text-gray-500">{m.email}</p>
                </div>
                <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-400">{m.role}</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No team members" description="Invite team members to collaborate on procurement analysis." />
        )}
      </div>
    </div>
  )
}

function RbacPanel() {
  const roles = useRoles()

  if (roles.isLoading) return <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}</div>

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Roles & Permissions</h2>
        {roles.data && roles.data.length > 0 ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {roles.data.map(role => (
              <div key={role.id} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-blue-500" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{role.name}</span>
                  {role.is_system && <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-gray-800">system</span>}
                </div>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{role.description}</p>
                {role.permissions.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {role.permissions.slice(0, 5).map(p => (
                      <span key={p} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-mono text-gray-600 dark:bg-gray-800 dark:text-gray-400">{p}</span>
                    ))}
                    {role.permissions.length > 5 && <span className="text-[10px] text-gray-400">+{role.permissions.length - 5}</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {['Admin', 'Manager', 'Analyst', 'Viewer'].map((role) => (
              <div key={role} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-blue-500" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{role}</span>
                </div>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  {role === 'Admin' && 'Full access to all features and settings'}
                  {role === 'Manager' && 'Can manage tenders and team members'}
                  {role === 'Analyst' && 'Can analyze tenders and view reports'}
                  {role === 'Viewer' && 'Read-only access to dashboard and reports'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SettingsPanel() {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Tenant Settings</h2>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Organization Name</label>
            <input className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" placeholder="Your Organization" defaultValue="" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Default Zone</label>
            <select className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
              <option>Zone A</option>
              <option>Zone B</option>
              <option>Zone C</option>
              <option>Zone D</option>
            </select>
          </div>
          <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">Save Settings</button>
        </div>
      </div>
    </div>
  )
}

function AuditLogPanel() {
  const logs = useAuditLogs(20)

  if (logs.isLoading) return <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-xl" />)}</div>

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Audit Log</h2>
        {logs.data?.audit_logs && logs.data.audit_logs.length > 0 ? (
          <div className="space-y-1">
            {logs.data.audit_logs.map(log => (
              <div key={log.id} className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 p-2 text-xs dark:border-gray-700 dark:bg-gray-800/60">
                <span className="rounded bg-gray-200 px-1.5 py-0.5 font-mono text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-400">{log.action}</span>
                <span className="text-gray-500">{log.resource_type ? `${log.resource_type} ` : ''}{log.resource_id ? `#${log.resource_id.slice(0, 8)}` : ''}</span>
                <span className="ml-auto text-gray-400">{new Date(log.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No audit logs" description="Audit log entries will appear as actions are performed." />
        )}
      </div>
    </div>
  )
}

export function EnterprisePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const activeTab = tabFromPath(location.pathname)

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Administration</h1>
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">Manage clients, team, roles, settings, and audit logs</p>
        </div>
      }
      primary={
        <Tabs value={activeTab} onValueChange={(v) => navigate(pathForTab(v as TabId), { replace: true })}>
          <TabsList>
            {TABS.map(t => (
              <TabsTrigger key={t.id} value={t.id}>
                <t.icon className="h-4 w-4 mr-2" />
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="clients"><ClientsPanel /></TabsContent>
          <TabsContent value="team"><TeamPanel /></TabsContent>
          <TabsContent value="rbac"><RbacPanel /></TabsContent>
          <TabsContent value="settings"><SettingsPanel /></TabsContent>
          <TabsContent value="audit"><AuditLogPanel /></TabsContent>
        </Tabs>
      }
    />
  )
}
