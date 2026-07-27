import clsx from 'clsx'
import { cn } from '@shared/lib/cn'

export interface ConfidenceMeterProps {
  value: number
  label?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

function bandForValue(value: number): { color: string; label: string } {
  if (value >= 80) return { color: 'text-success-700 dark:text-success-300', label: 'High' }
  if (value >= 50) return { color: 'text-warning-700 dark:text-warning-300', label: 'Medium' }
  return { color: 'text-danger-700 dark:text-danger-300', label: 'Low' }
}

const sizeStyles = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
}

const barColors = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
}

function barColor(value: number): string {
  if (value >= 80) return 'bg-success-700 dark:bg-success-300'
  if (value >= 50) return 'bg-warning-700 dark:bg-warning-300'
  return 'bg-danger-700 dark:bg-danger-300'
}

export function ConfidenceMeter({ value, label, size = 'md', className }: ConfidenceMeterProps) {
  const band = bandForValue(value)

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{label || 'Confidence'}</span>
        <span className={clsx('text-xs font-semibold tabular-nums', band.color)}>
          {Math.round(value)}% · {band.label}
        </span>
      </div>
      <div className={clsx('w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800', sizeStyles[size])}>
        <div
          className={clsx('h-full rounded-full transition-all duration-500', barColor(value), barColors[size])}
          style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
        />
      </div>
    </div>
  )
}
