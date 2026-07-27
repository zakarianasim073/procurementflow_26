import type { ReactNode } from 'react'
import clsx from 'clsx'
import { cn } from '@shared/lib/cn'
import { Sparkline } from './Sparkline'

export interface KpiCardProps {
  label: string
  value: string | number
  delta?: { value: string; direction: 'up' | 'down' | 'neutral' }
  icon?: ReactNode
  sparkData?: number[]
  sparkColor?: string
  isLoading?: boolean
  className?: string
}

export function KpiCard({ label, value, delta, icon, sparkData, sparkColor, isLoading, className }: KpiCardProps) {
  if (isLoading) {
    return (
      <div className={cn(
        'flex w-56 shrink-0 flex-col gap-2 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900',
        className
      )}>
        <div className="h-4 w-20 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
        <div className="h-8 w-32 animate-pulse rounded bg-gray-100 dark:bg-gray-800/60" />
        <div className="h-8 w-full animate-pulse rounded bg-gray-100 dark:bg-gray-800/60" />
      </div>
    )
  }

  return (
    <div className={cn(
      'flex w-56 shrink-0 flex-col gap-1 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900',
      className
    )}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</span>
        {icon && <span className="text-gray-400">{icon}</span>}
      </div>
      <span className="text-2xl font-bold tabular-nums text-gray-900 dark:text-white">{value}</span>
      {delta && (
        <span
          className={clsx(
            'inline-flex items-center gap-1 text-xs font-medium',
            delta.direction === 'up' && 'text-green-600 dark:text-green-400',
            delta.direction === 'down' && 'text-red-600 dark:text-red-400',
            delta.direction === 'neutral' && 'text-gray-500 dark:text-gray-400'
          )}
        >
          {delta.direction === 'up' && '↑'}
          {delta.direction === 'down' && '↓'}
          {delta.direction === 'neutral' && '→'}
          {delta.value}
        </span>
      )}
      {sparkData && sparkData.length > 0 && (
        <div className="mt-1 h-8">
          <Sparkline data={sparkData} color={sparkColor} height={32} />
        </div>
      )}
    </div>
  )
}
