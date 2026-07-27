import type { ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

export interface TrustPanelProps {
  confidence?: number
  verdict: 'passed' | 'warning' | 'needs_review' | 'unavailable'
  children: ReactNode
  className?: string
}

const verdictStyles = {
  passed: 'border-success-300 bg-success-50 dark:border-success-700 dark:bg-success-950/40',
  warning: 'border-warning-300 bg-warning-50 dark:border-warning-700 dark:bg-warning-950/40',
  needs_review: 'border-info-300 bg-info-50 dark:border-info-700 dark:bg-info-950/40',
  unavailable: 'border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900',
}

const verdictLabels = {
  passed: 'Passed',
  warning: 'Requires Attention',
  needs_review: 'Needs Review',
  unavailable: 'Evidence Unavailable',
}

export function TrustPanel({ confidence, verdict, children, className }: TrustPanelProps) {
  return (
    <div className={cn('rounded-xl border p-4', verdictStyles[verdict], className)}>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Trust &amp; Evidence
        </p>
        {confidence != null && (
          <span className="text-xs font-medium tabular-nums text-gray-600 dark:text-gray-300">
            {Math.round(confidence)}% confidence
          </span>
        )}
      </div>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-sm font-semibold text-gray-900 dark:text-white">
          {verdictLabels[verdict]}
        </span>
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">{children}</div>
    </div>
  )
}
