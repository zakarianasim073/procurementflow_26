import { type InputHTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: string
  error?: string
  leftAddon?: React.ReactNode
  rightAddon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, hint, error, leftAddon, rightAddon, className, id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftAddon && (
            <span className="absolute left-3 text-gray-400 dark:text-gray-500">{leftAddon}</span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              'h-9 w-full rounded-lg border bg-white px-3 text-sm text-gray-900 transition-colors',
              'placeholder:text-gray-400 dark:placeholder:text-gray-500',
              'dark:bg-gray-900 dark:text-white',
              'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1',
              'dark:focus:ring-offset-gray-900',
              error
                ? 'border-danger-300 focus:ring-danger-500 dark:border-danger-700'
                : 'border-gray-300 dark:border-gray-700',
              leftAddon && 'pl-9',
              rightAddon && 'pr-9',
              className,
            )}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
            {...props}
          />
          {rightAddon && (
            <span className="absolute right-3 text-gray-400 dark:text-gray-500">{rightAddon}</span>
          )}
        </div>
        {hint && !error && (
          <p id={`${inputId}-hint`} className="text-xs text-gray-500 dark:text-gray-400">{hint}</p>
        )}
        {error && (
          <p id={`${inputId}-error`} className="text-xs text-danger-700 dark:text-danger-300" role="alert">{error}</p>
        )}
      </div>
    )
  },
)
Input.displayName = 'Input'
