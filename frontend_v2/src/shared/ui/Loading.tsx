import clsx from 'clsx'
import { cn } from '../lib/cn'

export interface LoadingProps {
  label?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeStyles = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-[3px]',
}

export function Loading({ label = 'Loading...', size = 'md', className }: LoadingProps) {
  return (
    <div className={cn('flex items-center justify-center gap-2', className)} role="status" aria-label={label}>
      <span className={clsx('animate-spin rounded-full border-brand-200 border-t-brand-600 dark:border-brand-800 dark:border-t-brand-400', sizeStyles[size])} />
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
    </div>
  )
}
