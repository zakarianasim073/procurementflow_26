import { type HTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'

export interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  src?: string | null
  alt: string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  fallback?: string
}

const sizeStyles = {
  xs: 'h-6 w-6 text-[10px]',
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
  xl: 'h-16 w-16 text-lg',
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
}

const FALLBACK_COLORS = [
  'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300',
  'bg-success-300/30 text-success-700 dark:bg-success-300/20 dark:text-success-300',
  'bg-warning-300/30 text-warning-700 dark:bg-warning-300/20 dark:text-warning-300',
  'bg-info-300/30 text-info-700 dark:bg-info-300/20 dark:text-info-300',
]

function colorForName(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length]
}

export const Avatar = forwardRef<HTMLDivElement, AvatarProps>(
  ({ src, alt, size = 'md', fallback, className, ...props }, ref) => {
    const initials = fallback || getInitials(alt)

    if (src) {
      return (
        <div
          ref={ref}
          className={clsx('relative shrink-0 overflow-hidden rounded-full', sizeStyles[size], className)}
          {...props}
        >
          <img src={src} alt={alt} className="h-full w-full object-cover" />
        </div>
      )
    }

    return (
      <div
        ref={ref}
        role="img"
        aria-label={alt}
        className={clsx(
          'flex items-center justify-center rounded-full font-semibold',
          sizeStyles[size],
          colorForName(alt),
          className,
        )}
        {...props}
      >
        {initials}
      </div>
    )
  },
)
Avatar.displayName = 'Avatar'
