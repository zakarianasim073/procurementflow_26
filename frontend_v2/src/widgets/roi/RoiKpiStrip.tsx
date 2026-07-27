import { TrendingUp, AlertCircle } from 'lucide-react'

interface RoiKpiStripProps {
  hoursSaved: number
  complianceIssuesPrevented: number
  winRateImprovement: number
  valueCreated: number
}

export function RoiKpiStrip({
  hoursSaved,
  complianceIssuesPrevented,
  winRateImprovement,
  valueCreated,
}: RoiKpiStripProps) {
  const kpis = [
    {
      label: 'Hours Saved',
      value: hoursSaved.toLocaleString(),
      change: '+12%',
      icon: TrendingUp,
      color: 'blue',
    },
    {
      label: 'Issues Prevented',
      value: complianceIssuesPrevented,
      change: null,
      icon: AlertCircle,
      color: 'green',
    },
    {
      label: 'Win Rate ↑',
      value: `${winRateImprovement.toFixed(1)}%`,
      change: null,
      icon: TrendingUp,
      color: 'purple',
    },
    {
      label: 'Value Created',
      value: `${(valueCreated / 1e7).toFixed(1)}Cr`,
      change: null,
      icon: TrendingUp,
      color: 'orange',
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      {kpis.map((kpi) => {
        const Icon = kpi.icon
        const colorMap = {
          blue: 'border-blue-200 bg-blue-50 text-blue-600 dark:border-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
          green: 'border-green-200 bg-green-50 text-green-600 dark:border-green-700 dark:bg-green-900/30 dark:text-green-400',
          purple: 'border-purple-200 bg-purple-50 text-purple-600 dark:border-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
          orange: 'border-orange-200 bg-orange-50 text-orange-600 dark:border-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
        }

        return (
          <div
            key={kpi.label}
            className={`rounded-xl border ${colorMap[kpi.color as keyof typeof colorMap]} p-4`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-gray-600 dark:text-gray-400">{kpi.label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{kpi.value}</p>
              </div>
              <Icon className="h-5 w-5 opacity-60" />
            </div>
            {kpi.change && <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">{kpi.change} vs last month</p>}
          </div>
        )
      })}
    </div>
  )
}
