import { Avatar } from '@shared/ui'
import { cn } from '@shared/lib/cn'

export interface CompanyCardProps {
  name: string
  type?: string
  registrationNo?: string
  totalProjects?: number
  totalValue?: number
  onClick?: () => void
  className?: string
}

export function CompanyCard({ name, type, registrationNo, totalProjects, totalValue, onClick, className }: CompanyCardProps) {
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
      <div className="flex items-center gap-3">
        <Avatar alt={name} size="md" />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">{name}</h3>
          {type && <p className="text-xs text-gray-500 dark:text-gray-400">{type}</p>}
          {registrationNo && <p className="text-[10px] font-mono text-gray-400 dark:text-gray-500">{registrationNo}</p>}
        </div>
      </div>

      {(totalProjects != null || totalValue != null) && (
        <div className="mt-3 grid grid-cols-2 gap-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          {totalProjects != null && (
            <div>
              <p className="text-[10px] text-gray-400 dark:text-gray-500">Projects</p>
              <p className="text-sm font-semibold tabular-nums text-gray-900 dark:text-white">{totalProjects.toLocaleString()}</p>
            </div>
          )}
          {totalValue != null && (
            <div>
              <p className="text-[10px] text-gray-400 dark:text-gray-500">Total Value</p>
              <p className="text-sm font-semibold tabular-nums text-gray-900 dark:text-white">
                {totalValue >= 1e7 ? `${(totalValue / 1e7).toFixed(1)}Cr` : `${totalValue.toLocaleString()}`}
              </p>
            </div>
          )}
        </div>
      )}
    </button>
  )
}
