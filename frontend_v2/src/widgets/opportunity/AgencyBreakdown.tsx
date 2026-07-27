import type { AgencyItem } from '@entities/index'

interface AgencyBreakdownProps {
  agencies: AgencyItem[]
  isLoading?: boolean
}

export function AgencyBreakdown({ agencies, isLoading }: AgencyBreakdownProps) {
  if (isLoading) {
    return <div className="h-48 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
  }

  if (agencies.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 text-center dark:border-gray-800 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">No agency data available.</p>
      </div>
    )
  }

  const maxRates = Math.max(...agencies.map((a) => a.total_rates), 1)
  const top = agencies.slice(0, 10)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Agency Breakdown</h2>
      <div className="space-y-2">
        {top.map((a) => (
          <div key={a.name}>
            <div className="mb-0.5 flex items-center justify-between text-xs">
              <span className="font-medium text-gray-700 dark:text-gray-300">{a.name}</span>
              <span className="tabular-nums text-gray-500 dark:text-gray-400">{a.total_rates.toLocaleString()} rates</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
              <div
                className="h-full rounded-full bg-blue-500 dark:bg-blue-600"
                style={{ width: `${(a.total_rates / maxRates) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
