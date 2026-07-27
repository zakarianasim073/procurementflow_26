import type { AdminStats } from '@entities/admin'

interface Props {
  stats?: AdminStats
  isLoading?: boolean
  /** Per-tenant quota in GB; defaults to the backend's STORAGE_QUOTA_PER_TENANT_GB. */
  quotaGb?: number
}

export function StorageMetrics({ stats, isLoading, quotaGb = 100 }: Props) {
  if (isLoading) {
    return (
      <div className="h-48 rounded-lg border border-gray-200 bg-gray-50 animate-pulse dark:border-gray-800 dark:bg-gray-800" />
    )
  }

  if (!stats) return null

  const usagePercent = quotaGb > 0 ? (stats.storage_used_gb / quotaGb) * 100 : 0
  const warningThreshold = 80

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Storage Usage</h3>

      <div className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {stats.storage_used_gb.toFixed(2)} GB of {quotaGb} GB used
            </span>
            <span
              className={`text-sm font-medium ${
                usagePercent > warningThreshold
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-green-600 dark:text-green-400'
              }`}
            >
              {usagePercent.toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
            <div
              className={`h-full transition-all ${
                usagePercent > warningThreshold
                  ? 'bg-red-500'
                  : usagePercent > 50
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(usagePercent, 100)}%` }}
            />
          </div>
        </div>

        {usagePercent > warningThreshold && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 dark:bg-red-900/20 dark:border-red-800">
            <p className="text-sm text-red-800 dark:text-red-200">
              ⚠️ Storage usage is above {warningThreshold}%. Consider cleaning up old documents.
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <p className="text-gray-500 dark:text-gray-400">Available Storage</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white mt-1">
              {Math.max(0, quotaGb - stats.storage_used_gb).toFixed(2)} GB
            </p>
          </div>
          <div>
            <p className="text-gray-500 dark:text-gray-400">Documents</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white mt-1">
              {stats.total_documents}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
