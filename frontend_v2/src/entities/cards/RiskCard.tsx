import { AlertTriangle } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui'

export interface RiskCardProps {
  id: string
  title: string
  category: 'financial' | 'compliance' | 'operational' | 'market'
  severity: 'low' | 'medium' | 'high'
  description?: string
  mitigation?: string
  onClick?: () => void
  className?: string
}

const severityConfig = {
  low: { tone: 'info' as const, label: 'Low' },
  medium: { tone: 'warning' as const, label: 'Medium' },
  high: { tone: 'danger' as const, label: 'High' },
}

const categoryLabels = {
  financial: 'Financial',
  compliance: 'Compliance',
  operational: 'Operational',
  market: 'Market',
}

export function RiskCard({ title, category, severity, description, mitigation, onClick, className }: RiskCardProps) {
  const cfg = severityConfig[severity]

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
          <AlertTriangle size={14} className={cn(
            'mt-0.5 shrink-0',
            severity === 'high' ? 'text-danger-700 dark:text-danger-300' : 'text-warning-700 dark:text-warning-300',
          )} />
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
            <p className="text-[10px] text-gray-400 dark:text-gray-500">{categoryLabels[category]}</p>
          </div>
        </div>
        <Badge tone={cfg.tone} dot>{cfg.label}</Badge>
      </div>
      {description && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-2">{description}</p>
      )}
      {mitigation && (
        <p className="mt-1 text-[10px] text-success-700 dark:text-success-300">Mitigation: {mitigation}</p>
      )}
    </button>
  )
}
