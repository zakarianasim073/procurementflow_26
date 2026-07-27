import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

interface WidgetFooterProps {
  children?: ReactNode
  className?: string
}

export function WidgetFooter({ children, className }: WidgetFooterProps) {
  if (!children) return null
  return (
    <div className={cn('border-t border-gray-100 px-4 py-2 dark:border-gray-800', className)}>
      {children}
    </div>
  )
}
