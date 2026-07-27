import type { SystemHealth } from '@entities/admin'

interface Props {
  health?: SystemHealth
  isLoading?: boolean
}

const STATUS_COLORS: Record<string, string> = {
  healthy: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
  degraded: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200',
  unhealthy: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
}

const STATUS_ICONS: Record<string, string> = {
  healthy: '✅',
  degraded: '⚠️',
  unhealthy: '❌',
}

export function SystemHealthStatus({ health, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="h-32 rounded-lg border border-gray-200 bg-gray-50 animate-pulse dark:border-gray-800 dark:bg-gray-800" />
    )
  }

  if (!health) return null

  const status = health.status ?? 'unknown'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">{STATUS_ICONS[status] ?? '•'}</span>
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">System Status</h3>
          <span
            className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${
              STATUS_COLORS[status] ?? STATUS_COLORS.degraded
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <HealthRow label="API routers" ok={health.api_routers_loaded} />
        <HealthRow label="Agent runtime" ok={health.agent_runtime_ready} />
      </div>
    </div>
  )
}

function HealthRow({ label, ok }: { label: string; ok?: boolean }) {
  if (ok === undefined) return null
  return (
    <div className="flex items-center gap-2">
      <span className={`text-lg ${ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
        {ok ? '●' : '○'}
      </span>
      <span className="text-gray-700 dark:text-gray-300">{label}</span>
    </div>
  )
}
