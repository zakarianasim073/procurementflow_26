import type { ReactNode } from 'react'
import { cn } from '../lib/cn'

export interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50/50 px-6 py-12 text-center dark:border-gray-700 dark:bg-gray-900/50',
        className,
      )}
    >
      {icon && (
        <div className="mb-3 text-gray-400 dark:text-gray-500">{icon}</div>
      )}
      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-xs text-gray-500 dark:text-gray-400">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
