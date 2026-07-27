import { type HTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'
import { cn } from '../lib/cn'

export interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number
  max?: number
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const variantStyles = {
  default: 'bg-brand-600 dark:bg-brand-500',
  success: 'bg-success-700 dark:bg-success-300',
  warning: 'bg-warning-700 dark:bg-warning-300',
  danger: 'bg-danger-700 dark:bg-danger-300',
  info: 'bg-info-700 dark:bg-info-300',
}

const sizeStyles = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
}

export const Progress = forwardRef<HTMLDivElement, ProgressProps>(
  ({ value, max = 100, variant = 'default', size = 'md', showLabel, className, ...props }, ref) => {
    const pct = Math.min(Math.max((value / max) * 100, 0), 100)

    return (
      <div className="flex flex-col gap-1" ref={ref} {...props}>
        {showLabel && (
          <span className="text-xs font-medium tabular-nums text-gray-600 dark:text-gray-400">
            {Math.round(pct)}%
          </span>
        )}
        <div
          className={cn(
            'w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800',
            sizeStyles[size],
            className,
          )}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        >
          <div
            className={clsx('h-full rounded-full transition-all duration-300', variantStyles[variant])}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    )
  },
)
Progress.displayName = 'Progress'
