import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui'

export interface SubmissionCardProps {
  id: string
  tenderTitle: string
  submittedAt?: string
  status: 'preparing' | 'submitted' | 'under_review' | 'accepted' | 'rejected'
  quotedAmount?: number
  className?: string
}

const statusConfig = {
  preparing: { tone: 'default' as const, label: 'Preparing' },
  submitted: { tone: 'info' as const, label: 'Submitted' },
  under_review: { tone: 'warning' as const, label: 'Under Review' },
  accepted: { tone: 'success' as const, label: 'Accepted' },
  rejected: { tone: 'danger' as const, label: 'Rejected' },
}

export function SubmissionCard({ tenderTitle, submittedAt, status, quotedAmount, className }: SubmissionCardProps) {
  const cfg = statusConfig[status]

  return (
    <div className={cn(
      'rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900',
      className,
    )}>
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white line-clamp-2">{tenderTitle}</h3>
        <Badge tone={cfg.tone} dot>{cfg.label}</Badge>
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        {submittedAt && <span>Submitted {new Date(submittedAt).toLocaleDateString()}</span>}
        {quotedAmount != null && (
          <span className="font-semibold tabular-nums text-gray-900 dark:text-white">
            {quotedAmount >= 1e7 ? `${(quotedAmount / 1e7).toFixed(1)}Cr` : `${quotedAmount.toLocaleString()}`} BDT
          </span>
        )}
      </div>
    </div>
  )
}
