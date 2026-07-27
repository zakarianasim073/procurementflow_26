import type { ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

export interface ReasoningPanelProps {
  title?: string
  children: ReactNode
  evidence?: ReactNode
  className?: string
}

export function ReasoningPanel({ title = 'Reasoning', children, evidence, className }: ReasoningPanelProps) {
  return (
    <div className={cn('rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900', className)}>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{title}</p>
      <div className="text-sm text-gray-700 dark:text-gray-300">{children}</div>
      {evidence && (
        <div className="mt-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          {evidence}
        </div>
      )}
    </div>
  )
}
