import { Calendar, MapPin } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui'
import { ConfidenceMeter } from '@widgets/ai/ConfidenceMeter'

export interface TenderCardProps {
  id: string
  title: string
  agency: string
  packageNo: string
  estimatedValue?: number
  closingDate: string
  district?: string
  winProbability?: number
  status: 'live' | 'closing_soon' | 'expired' | 'archived'
  onClick?: () => void
  className?: string
}

const statusConfig = {
  live: { tone: 'success' as const, label: 'Live' },
  closing_soon: { tone: 'warning' as const, label: 'Closing Soon' },
  expired: { tone: 'danger' as const, label: 'Expired' },
  archived: { tone: 'default' as const, label: 'Archived' },
}

function formatValue(value?: number): string {
  if (value == null) return '—'
  if (value <= 0) return 'Not available'
  if (value >= 1e7) return `৳${(value / 1e7).toLocaleString(undefined, { maximumFractionDigits: 2 })} Cr`
  if (value >= 1e5) return `৳${(value / 1e5).toLocaleString(undefined, { maximumFractionDigits: 2 })} Lakh`
  return `৳${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

export function TenderCard({ title, agency, packageNo, estimatedValue, closingDate, district, winProbability, status, onClick, className }: TenderCardProps) {
  const cfg = statusConfig[status]

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full rounded-xl border border-gray-200 bg-white p-4 text-left transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-900',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        onClick && 'cursor-pointer',
        className,
      )}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white line-clamp-2">{title}</h3>
        <Badge tone={cfg.tone} dot>{cfg.label}</Badge>
      </div>

      <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
        <span>{agency}</span>
        <span className="font-mono">{packageNo}</span>
        {district && (
          <span className="flex items-center gap-1">
            <MapPin size={10} />{district}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Est. Value</p>
          <p className="text-sm font-semibold tabular-nums text-gray-900 dark:text-white">{formatValue(estimatedValue)}</p>
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          <Calendar size={10} />
          {new Date(closingDate).toLocaleDateString()}
        </div>
      </div>

      {winProbability != null && (
        <div className="mt-3">
          <ConfidenceMeter value={winProbability} label="Win Probability" size="sm" />
        </div>
      )}
    </button>
  )
}
