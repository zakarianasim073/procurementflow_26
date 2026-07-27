import { Scale } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui'

export interface RuleCardProps {
  ruleCode: string
  title: string
  section?: string
  status: 'passed' | 'warning' | 'failed' | 'not_applicable'
  detail?: string
  onClick?: () => void
  className?: string
}

const statusConfig = {
  passed: { tone: 'success' as const, label: 'Passed' },
  warning: { tone: 'warning' as const, label: 'Requires Attention' },
  failed: { tone: 'danger' as const, label: 'Failed' },
  not_applicable: { tone: 'default' as const, label: 'N/A' },
}

export function RuleCard({ ruleCode, title, section, status, detail, onClick, className }: RuleCardProps) {
  const cfg = statusConfig[status]

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full rounded-xl border border-gray-200 bg-white p-4 text-left transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-900',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <Scale size={14} className="mt-0.5 shrink-0 text-gray-400 dark:text-gray-500" />
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
            <p className="text-xs font-mono text-gray-500 dark:text-gray-400">{ruleCode}</p>
            {section && <p className="text-[10px] text-gray-400 dark:text-gray-500">{section}</p>}
          </div>
        </div>
        <Badge tone={cfg.tone} dot>{cfg.label}</Badge>
      </div>
      {detail && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-2">{detail}</p>
      )}
    </button>
  )
}
