import { type HTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded'
  width?: string | number
  height?: string | number
  lines?: number
}

const variantStyles = {
  text: 'rounded',
  circular: 'rounded-full',
  rectangular: '',
  rounded: 'rounded-xl',
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ variant = 'text', width, height, lines = 1, className, ...props }, ref) => {
    if (lines > 1) {
      return (
        <div ref={ref} className="space-y-2" {...props}>
          {Array.from({ length: lines }).map((_, i) => (
            <div
              key={i}
              className={clsx(
                'animate-pulse bg-gray-200 dark:bg-gray-800',
                variantStyles[variant],
                i === lines - 1 && 'w-3/4',
                className,
              )}
              style={{ width: i === lines - 1 ? undefined : width, height }}
            />
          ))}
        </div>
      )
    }

    return (
      <div
        ref={ref}
        className={clsx(
          'animate-pulse bg-gray-200 dark:bg-gray-800',
          variantStyles[variant],
          className,
        )}
        style={{ width, height }}
        {...props}
      />
    )
  },
)
Skeleton.displayName = 'Skeleton'
