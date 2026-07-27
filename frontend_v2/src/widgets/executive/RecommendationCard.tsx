import { Shield } from 'lucide-react'

interface RecommendationCardProps {
  decision: 'Bidding Recommended' | 'Marginal Value (Proceed with Caution)' | 'Do Not Bid'
  probability: string
  confidence: string
  strategy?: string
  actionItems?: string[]
}

const DECISION_COLORS = {
  'Bidding Recommended': {
    badge: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
    icon: 'bg-green-500',
  },
  'Marginal Value (Proceed with Caution)': {
    badge: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
    icon: 'bg-yellow-500',
  },
  'Do Not Bid': {
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
    icon: 'bg-red-500',
  },
}

export function RecommendationCard({
  decision,
  probability,
  confidence,
  strategy,
  actionItems,
}: RecommendationCardProps) {
  const colors = DECISION_COLORS[decision] ?? DECISION_COLORS['Do Not Bid']

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-3 flex items-center gap-2">
        <Shield size={16} className="text-gray-400" />
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          AI Forecast
        </span>
      </div>

      <span className={`mb-3 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${colors.badge}`}>
        {decision}
      </span>

      <div className="mb-3 space-y-1">
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">Win Probability</span>
          <span className="text-lg font-bold tabular-nums text-gray-900 dark:text-white">{probability}</span>
        </div>
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">Confidence Score</span>
          <span className="text-sm font-medium tabular-nums text-gray-700 dark:text-gray-300">{confidence}</span>
        </div>
      </div>

      {strategy && (
        <p className="mb-3 text-xs leading-relaxed text-gray-600 dark:text-gray-400">{strategy}</p>
      )}

      {actionItems && actionItems.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Next actions</p>
          <ul className="space-y-1">
            {actionItems.slice(0, 3).map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                <span className="mt-0.5 h-1 w-1 shrink-0 rounded-full bg-gray-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export function RecommendationCardSkeleton() {
  return (
    <div className="h-52 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
  )
}
