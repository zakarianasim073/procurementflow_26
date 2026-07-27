import { type HTMLAttributes, type ReactNode, forwardRef } from 'react'
import clsx from 'clsx'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'interactive'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  children: ReactNode
}

const paddingStyles = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant = 'default', padding = 'md', className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={clsx(
        'rounded-xl border bg-white dark:bg-gray-900',
        variant === 'default' && 'border-gray-200 dark:border-gray-800',
        variant === 'interactive' && 'border-gray-200 dark:border-gray-800 transition-shadow hover:shadow-md cursor-pointer',
        paddingStyles[padding],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  ),
)
Card.displayName = 'Card'

export function CardHeader({ className, children, ...props }: HTMLAttributes<HTMLDivElement> & { children?: ReactNode }) {
  return <div className={clsx('border-b border-gray-200 px-4 py-3 dark:border-gray-800', className)} {...props}>{children}</div>
}

export function CardTitle({ className, children, ...props }: HTMLAttributes<HTMLHeadingElement> & { children?: ReactNode }) {
  return <h3 className={clsx('text-base font-semibold text-gray-900 dark:text-white', className)} {...props}>{children}</h3>
}

export function CardContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement> & { children?: ReactNode }) {
  return <div className={clsx('px-4 py-3', className)} {...props}>{children}</div>
}
