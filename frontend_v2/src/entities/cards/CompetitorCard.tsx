import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@shared/lib/cn'

export interface CompetitorCardProps {
  name: string
  winRate?: number
  totalBids?: number
  avgBid?: number
  similarProjects?: number
  onClick?: () => void
  className?: string
}

export function CompetitorCard({ name, winRate, totalBids, avgBid, similarProjects, onClick, className }: CompetitorCardProps) {
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
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">{name}</h3>
        {winRate != null && (
          <span className={cn(
            'flex items-center gap-1 text-xs font-semibold tabular-nums',
            winRate >= 30 ? 'text-success-700 dark:text-success-300' : 'text-gray-500 dark:text-gray-400',
          )}>
            {winRate >= 30 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {winRate.toFixed(1)}%
          </span>
        )}
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-gray-500 dark:text-gray-400">
        {totalBids != null && (
          <div>
            <p className="text-[10px]">Total Bids</p>
            <p className="font-semibold tabular-nums text-gray-900 dark:text-white">{totalBids.toLocaleString()}</p>
          </div>
        )}
        {avgBid != null && (
          <div>
            <p className="text-[10px]">Avg. Bid</p>
            <p className="font-semibold tabular-nums text-gray-900 dark:text-white">
              {avgBid >= 1e7 ? `${(avgBid / 1e7).toFixed(1)}Cr` : `${(avgBid / 1e5).toFixed(1)}L`}
            </p>
          </div>
        )}
        {similarProjects != null && (
          <div>
            <p className="text-[10px]">Similar</p>
            <p className="font-semibold tabular-nums text-gray-900 dark:text-white">{similarProjects}</p>
          </div>
        )}
      </div>
    </button>
  )
}
