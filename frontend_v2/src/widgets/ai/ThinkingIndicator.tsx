import { cn } from '@shared/lib/cn'

export interface ThinkingIndicatorProps {
  label?: string
  className?: string
}

export function ThinkingIndicator({ label = 'AI is working...', className }: ThinkingIndicatorProps) {
  return (
    <div
      className={cn('flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-900', className)}
      role="status"
      aria-label={label}
    >
      <div className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-600 [animation-delay:-0.3s] dark:bg-brand-400" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-600 [animation-delay:-0.15s] dark:bg-brand-400" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-600 dark:bg-brand-400" />
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
    </div>
  )
}
