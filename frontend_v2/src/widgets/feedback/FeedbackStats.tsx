import { BarChart3, TrendingUp, Clock, CheckCircle } from 'lucide-react'
import { useFeedbackStats } from '@hooks/feedback'

export function FeedbackStats() {
  const { data: stats, isLoading } = useFeedbackStats()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="animate-pulse space-y-3">
              <div className="h-4 w-24 rounded bg-gray-200 dark:bg-gray-700"></div>
              <div className="h-8 w-16 rounded bg-gray-200 dark:bg-gray-700"></div>
              <div className="h-3 w-32 rounded bg-gray-200 dark:bg-gray-700"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        No feedback statistics available
      </div>
    )
  }

  const statsCards = [
    {
      key: 'total_recommended',
      title: 'Total Recommended',
      value: stats.total_tenders_recommended || 0,
      icon: BarChart3,
      color: 'blue',
      change: null,
    },
    {
      key: 'bids_placed',
      title: 'Bids Placed',
      value: stats.bids_placed || 0,
      icon: Clock,
      color: 'yellow',
      change: null,
    },
    {
      key: 'won_tenders',
      title: 'Tenders Won',
      value: stats.won_tenders || 0,
      icon: CheckCircle,
      color: 'green',
      change: null,
    },
    {
      key: 'win_rate',
      title: 'Win Rate',
      value: stats.win_rate ? `${(stats.win_rate * 100).toFixed(0)}%` : '0%',
      icon: TrendingUp,
      color: 'purple',
      change: null,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      {statsCards.map((card) => {
        const Icon = card.icon
        const colorClasses = {
          blue: 'bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-700',
          yellow: 'bg-yellow-50 text-yellow-600 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-700',
          green: 'bg-green-50 text-green-600 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-700',
          purple: 'bg-purple-50 text-purple-600 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-700',
        }

        return (
          <div key={card.key} className={`rounded-xl border ${colorClasses[card.color as keyof typeof colorClasses]} p-4 shadow-sm transition-all hover:shadow-md`}>
            <div className="flex items-center justify-between mb-2">
              <div className="rounded-lg bg-white p-2 shadow-sm dark:bg-gray-800">
                <Icon className="h-4 w-4" />
              </div>
              {card.change !== null && (
                <div className={`flex items-center gap-1 text-xs font-medium ${card.change >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  <TrendingUp className={`h-3 w-3 ${card.change < 0 ? 'rotate-180' : ''}`} />
                  {Math.abs(card.change)}%
                </div>
              )}
            </div>
            <div>
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400">{card.title}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{card.value}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
