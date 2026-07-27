import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

interface WidgetToolbarProps {
  children?: ReactNode
  className?: string
}

export function WidgetToolbar({ children, className }: WidgetToolbarProps) {
  if (!children) return null
  return (
    <div className={cn('flex flex-wrap items-center gap-2 border-b border-gray-100 px-4 py-2 dark:border-gray-800', className)}>
      {children}
    </div>
  )
}

interface ToolbarButtonProps {
  icon: ReactNode
  label: string
  onClick?: () => void
  active?: boolean
  className?: string
}

export function ToolbarButton({ icon, label, onClick, active, className }: ToolbarButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
        'hover:bg-gray-100 dark:hover:bg-gray-800',
        active ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-300' : 'text-gray-600 dark:text-gray-400',
        className,
      )}
      title={label}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  )
}
