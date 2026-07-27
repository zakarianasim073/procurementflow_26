import { type ReactNode, type SelectHTMLAttributes } from 'react'
import { cn } from '@shared/lib/cn'

interface WidgetFiltersProps {
  children: ReactNode
  className?: string
}

export function WidgetFilters({ children, className }: WidgetFiltersProps) {
  return (
    <div className={cn('flex flex-wrap items-center gap-2 border-b border-gray-100 px-4 py-2 dark:border-gray-800', className)}>
      {children}
    </div>
  )
}

interface FilterSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
}

export function FilterSelect({ label, className, children, ...props }: FilterSelectProps) {
  return (
    <div className="flex items-center gap-1.5">
      {label && <label className="text-[11px] font-medium text-gray-500 dark:text-gray-400">{label}</label>}
      <select
        className={cn(
          'rounded-md border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700',
          'focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400',
          'dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300',
          className,
        )}
        {...props}
      >
        {children}
      </select>
    </div>
  )
}

interface FilterInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export function FilterInput({ value, onChange, placeholder = 'Search...', className }: FilterInputProps) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={cn(
        'rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-700 placeholder-gray-400',
        'focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400',
        'dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:placeholder-gray-500',
        'w-48',
        className,
      )}
    />
  )
}
