import { type HTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'

export interface ChipProps extends HTMLAttributes<HTMLSpanElement> {
  removable?: boolean
  onRemove?: () => void
  active?: boolean
}

export const Chip = forwardRef<HTMLSpanElement, ChipProps>(
  ({ removable, onRemove, active, className, children, ...props }, ref) => (
    <span
      ref={ref}
      className={clsx(
        'inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium transition-colors',
        active
          ? 'border-brand-300 bg-brand-50 text-brand-700 dark:border-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
          : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-800',
        className,
      )}
      {...props}
    >
      {children}
      {removable && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onRemove?.()
          }}
          className="ml-0.5 rounded-full p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700"
          aria-label="Remove"
        >
          <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 3l6 6M9 3l-6 6" />
          </svg>
        </button>
      )}
    </span>
  ),
)
Chip.displayName = 'Chip'
