import { cn } from '@shared/lib/cn'

export interface BoqCardProps {
  id: string
  itemCode: string
  description: string
  unit: string
  quantity: number
  sorRate?: number
  variance?: number
  onClick?: () => void
  className?: string
}

function varianceColor(variance?: number): string {
  if (variance == null) return ''
  if (variance > 10) return 'text-danger-700 dark:text-danger-300'
  if (variance < -10) return 'text-warning-700 dark:text-warning-300'
  return 'text-success-700 dark:text-success-300'
}

export function BoqCard({ itemCode, description, unit, quantity, sorRate, variance, onClick, className }: BoqCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full rounded-xl border border-gray-200 bg-white p-4 text-left transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-900',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-mono text-gray-500 dark:text-gray-400">{itemCode}</p>
          <h3 className="text-sm font-medium text-gray-900 dark:text-white">{description}</h3>
        </div>
        {variance != null && (
          <span className={cn('text-xs font-semibold tabular-nums', varianceColor(variance))}>
            {variance > 0 ? '+' : ''}{variance.toFixed(1)}%
          </span>
        )}
      </div>
      <div className="mt-2 flex gap-4 text-xs text-gray-500 dark:text-gray-400">
        <span>{quantity.toLocaleString()} {unit}</span>
        {sorRate != null && (
          <span>SOR: {sorRate.toLocaleString()} BDT/{unit}</span>
        )}
      </div>
    </button>
  )
}
