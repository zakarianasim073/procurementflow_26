import { ScreenTemplate } from '@layouts/index'
import { useAdminStats, useSystemHealth } from '@hooks/index'
import { StorageMetrics } from './StorageMetrics'
import { SystemHealthStatus } from './SystemHealthStatus'

export function AdminDashboard() {
  const { data: stats, isLoading: statsLoading } = useAdminStats()
  const { data: health, isLoading: healthLoading } = useSystemHealth()

  return (
    <ScreenTemplate
      header={
        <>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Admin Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            System overview and management
          </p>
        </>
      }
      primary={
        <div className="space-y-6">
          {/* System Health */}
          <SystemHealthStatus health={health} isLoading={healthLoading} />

          {/* Statistics Cards */}
          {statsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-24 rounded-lg border border-gray-200 bg-gray-50 animate-pulse dark:border-gray-800 dark:bg-gray-800"
                />
              ))}
            </div>
          ) : stats ? (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <StatCard
                title="Total Users"
                value={stats.total_users}
                icon="👥"
              />
              <StatCard
                title="Total Tenders"
                value={stats.total_tenders}
                icon="📋"
              />
              <StatCard
                title="Total Documents"
                value={stats.total_documents}
                icon="📄"
              />
              <StatCard
                title="Storage Used"
                value={`${stats.storage_used_gb.toFixed(2)} GB`}
                subtitle={`${stats.total_users} users`}
                icon="💾"
              />
            </div>
          ) : null}

          {/* Storage Metrics */}
          <StorageMetrics stats={stats} isLoading={statsLoading} />
        </div>
      }
    />
  )
}

function StatCard({ title, value, subtitle, icon }: any) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
          {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  )
}
