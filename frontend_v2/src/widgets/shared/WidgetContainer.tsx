import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

interface WidgetContainerProps {
  children: ReactNode
  className?: string
  fullscreen?: boolean
}

export function WidgetContainer({ children, className, fullscreen }: WidgetContainerProps) {
  return (
    <div
      className={cn(
        'flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700/50 dark:bg-gray-900',
        fullscreen ? 'fixed inset-0 z-50 rounded-none border-0' : '',
        className,
      )}
    >
      {children}
    </div>
  )
}
