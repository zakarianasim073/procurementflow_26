import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

interface DashboardGridProps {
  children: ReactNode
  className?: string
  columns?: 1 | 2 | 3 | 4
}

const GRID_COLS = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 md:grid-cols-2',
  3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
}

export function DashboardGrid({ children, className, columns = 3 }: DashboardGridProps) {
  return (
    <div className={cn('grid gap-4', GRID_COLS[columns], className)}>
      {children}
    </div>
  )
}
