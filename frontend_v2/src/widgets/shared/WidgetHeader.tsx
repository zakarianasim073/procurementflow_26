import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

interface WidgetHeaderProps {
  title: string
  subtitle?: string
  icon?: ReactNode
  actions?: ReactNode
  className?: string
}

export function WidgetHeader({ title, subtitle, icon, actions, className }: WidgetHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800', className)}>
      <div className="flex items-center gap-2.5">
        {icon && <span className="text-gray-500 dark:text-gray-400">{icon}</span>}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
          {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
