import { AlertTriangle, CheckCircle, Clock } from 'lucide-react'

interface UrgentActionsPanelProps {
  actionItems?: string[]
  liveTenders?: number
  isLoading?: boolean
}

function priorityIcon(item: string) {
  const lower = item.toLowerCase()
  if (lower.includes('submit') || lower.includes('bid security') || lower.includes('pay order')) return 'urgent'
  if (lower.includes('verify') || lower.includes('approve') || lower.includes('train')) return 'pending'
  return 'info'
}

export function UrgentActionsPanel({ actionItems, liveTenders, isLoading }: UrgentActionsPanelProps) {
  if (isLoading) {
    return <ActionsSkeleton />
  }

  if (!actionItems || actionItems.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <CheckCircle size={16} className="text-green-500" />
          No urgent actions. All pipeline items are on track.
        </div>
      </div>
    )
  }

  const critical = actionItems.filter((i) => priorityIcon(i) === 'urgent')
  const other = actionItems.filter((i) => priorityIcon(i) !== 'urgent')

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          {critical.length > 0 ? 'Requires Attention' : 'Recommended Actions'}
        </h2>
        {liveTenders != null && (
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {liveTenders.toLocaleString()} live
          </span>
        )}
      </div>

      <ul className="space-y-2">
        {[...critical, ...other].map((item, i) => {
          const pri = priorityIcon(item)
          return (
            <li key={i} className="flex items-start gap-2 text-sm">
              {pri === 'urgent' && (
                <AlertTriangle size={14} className="mt-0.5 shrink-0 text-red-500" />
              )}
              {pri === 'pending' && (
                <Clock size={14} className="mt-0.5 shrink-0 text-yellow-500" />
              )}
              {pri === 'info' && (
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400" />
              )}
              <span className="text-gray-700 dark:text-gray-300">{item}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function ActionsSkeleton() {
  return <div className="h-28 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
}
