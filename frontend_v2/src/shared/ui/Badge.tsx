import { type HTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'

export type BadgeTone = 'default' | 'success' | 'warning' | 'danger' | 'info'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  dot?: boolean
  variant?: 'solid' | 'outline'
}

const toneStyles: Record<BadgeTone, string> = {
  default: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  success: 'bg-success-50 text-success-700 dark:bg-success-950 dark:text-success-300',
  warning: 'bg-warning-50 text-warning-700 dark:bg-warning-950 dark:text-warning-300',
  danger: 'bg-danger-50 text-danger-700 dark:bg-danger-950 dark:text-danger-300',
  info: 'bg-info-50 text-info-700 dark:bg-info-950 dark:text-info-300',
}

const dotStyles: Record<BadgeTone, string> = {
  default: 'bg-gray-500',
  success: 'bg-success-700 dark:bg-success-300',
  warning: 'bg-warning-700 dark:bg-warning-300',
  danger: 'bg-danger-700 dark:bg-danger-300',
  info: 'bg-info-700 dark:bg-info-300',
}

const outlineToneStyles: Record<BadgeTone, string> = {
  default: 'border-gray-200 text-gray-700 dark:border-gray-700 dark:text-gray-300',
  success: 'border-success-200 text-success-700 dark:border-success-800 dark:text-success-300',
  warning: 'border-warning-200 text-warning-700 dark:border-warning-800 dark:text-warning-300',
  danger: 'border-danger-200 text-danger-700 dark:border-danger-800 dark:text-danger-300',
  info: 'border-info-200 text-info-700 dark:border-info-800 dark:text-info-300',
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ tone = 'default', dot, variant, className, children, ...props }, ref) => (
    <span
      ref={ref}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium',
        variant === 'outline' ? outlineToneStyles[tone] : toneStyles[tone],
        className,
      )}
      {...props}
    >
      {dot && <span className={clsx('h-1.5 w-1.5 rounded-full', dotStyles[tone])} />}
      {children}
    </span>
  ),
)
Badge.displayName = 'Badge'
