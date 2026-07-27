import { Trophy } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui'

export interface AwardCardProps {
  id: string
  tenderTitle: string
  agency: string
  packageNo: string
  awardedAmount: number
  awardedDate: string
  status: 'awarded' | 'in_progress' | 'completed' | 'disputed'
  className?: string
}

const statusConfig = {
  awarded: { tone: 'success' as const, label: 'Awarded' },
  in_progress: { tone: 'info' as const, label: 'In Progress' },
  completed: { tone: 'success' as const, label: 'Completed' },
  disputed: { tone: 'danger' as const, label: 'Disputed' },
}

export function AwardCard({ tenderTitle, agency, packageNo, awardedAmount, awardedDate, status, className }: AwardCardProps) {
  const cfg = statusConfig[status]

  return (
    <div className={cn(
      'rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900',
      className,
    )}>
      <div className="flex items-start gap-2">
        <Trophy size={14} className="mt-0.5 shrink-0 text-warning-700 dark:text-warning-300" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white line-clamp-2">{tenderTitle}</h3>
            <Badge tone={cfg.tone} dot>{cfg.label}</Badge>
          </div>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500 dark:text-gray-400">
            <span>{agency}</span>
            <span className="font-mono">{packageNo}</span>
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3 dark:border-gray-800">
        <div>
          <p className="text-[10px] text-gray-400 dark:text-gray-500">Awarded Amount</p>
          <p className="text-sm font-semibold tabular-nums text-gray-900 dark:text-white">
            {awardedAmount >= 1e7 ? `${(awardedAmount / 1e7).toFixed(1)}Cr` : `${awardedAmount.toLocaleString()}`} BDT
          </p>
        </div>
        <time className="text-xs text-gray-500 dark:text-gray-400">
          {new Date(awardedDate).toLocaleDateString()}
        </time>
      </div>
    </div>
  )
}
