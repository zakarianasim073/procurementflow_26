import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

interface WidgetContentProps {
  children: ReactNode
  className?: string
  scrollable?: boolean
}

export function WidgetContent({ children, className, scrollable = true }: WidgetContentProps) {
  return (
    <div className={cn('flex-1', scrollable ? 'overflow-auto' : '', className)}>
      {children}
    </div>
  )
}
