import { cn } from '@shared/lib/cn'

export interface EvidenceEntry {
  id: string
  source: string
  title: string
  excerpt?: string
  timestamp: string
  score?: number
}

export interface EvidenceTimelineProps {
  entries: EvidenceEntry[]
  compact?: boolean
  className?: string
}

export function EvidenceTimeline({ entries, compact, className }: EvidenceTimelineProps) {
  if (entries.length === 0) {
    return (
      <div className={cn('rounded-xl border border-dashed border-gray-300 bg-gray-50/50 p-4 text-center dark:border-gray-700 dark:bg-gray-900/50', className)}>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Evidence unavailable for this recommendation — it can&apos;t be shown until sourced.
        </p>
      </div>
    )
  }

  return (
    <div className={cn('relative space-y-3', compact ? 'pl-4' : 'pl-5', className)}>
      <div className="absolute left-1.5 top-1 bottom-1 w-px bg-gray-200 dark:bg-gray-800" />
      {entries.map((entry) => (
        <div key={entry.id} className="relative flex gap-3">
          <div className="absolute left-[-14px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white bg-brand-600 dark:border-gray-900" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-900 dark:text-white">{entry.title}</span>
              {entry.score != null && (
                <span className="shrink-0 rounded-full bg-brand-50 px-1.5 py-0.5 text-[10px] font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
                  {Math.round(entry.score)}%
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">{entry.source}</p>
            {entry.excerpt && !compact && (
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400 line-clamp-2">{entry.excerpt}</p>
            )}
            <time className="mt-0.5 block text-[10px] text-gray-400 dark:text-gray-500">
              {new Date(entry.timestamp).toLocaleDateString()}
            </time>
          </div>
        </div>
      ))}
    </div>
  )
}
