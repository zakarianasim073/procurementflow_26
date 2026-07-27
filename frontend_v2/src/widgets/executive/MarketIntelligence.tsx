import { Building2, TrendingUp, DollarSign, Award } from 'lucide-react'
import { useLiveMetrics } from '@hooks/index'

export function MarketIntelligence() {
  const { data, isLoading } = useLiveMetrics()

  if (isLoading) {
    return <MarketIntelSkeleton />
  }

  if (!data) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Awaiting market data. Start scanning tenders.
        </p>
      </div>
    )
  }

  const { overview, top_agencies, top_contractors } = data

  return (
    <div className="space-y-3">
      {/* Market Snapshot */}
      <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Market Snapshot
        </h2>
        <div className="grid grid-cols-2 gap-2">
          <StatBlock icon={TrendingUp} label="Total Tenders" value={overview.total_tenders.toLocaleString()} />
          <StatBlock icon={DollarSign} label="Total Value" value={`${(overview.total_value_bdt / 1e7).toFixed(0)}Cr`} />
          <StatBlock icon={Building2} label="Avg Value" value={`${(overview.avg_value_bdt / 1e7).toFixed(1)}Cr`} />
          <StatBlock icon={Award} label="Awarded" value={overview.awarded_count.toLocaleString()} />
        </div>
      </div>

      {/* Top Agencies */}
      <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Top Agencies
        </h2>
        {top_agencies.length === 0 ? (
          <p className="text-xs text-gray-400">No agency data available.</p>
        ) : (
          <ul className="space-y-1.5">
            {top_agencies.slice(0, 5).map((a) => {
              const maxTenders = top_agencies[0].tender_count || 1
              const pct = (a.tender_count / maxTenders) * 100
              return (
                <li key={a.agency_code} className="flex items-center gap-2 text-xs">
                  <span className="w-4 shrink-0 font-medium text-gray-700 dark:text-gray-300">{a.agency_code}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                    <div
                      className="h-full rounded-full bg-blue-500 dark:bg-blue-600"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="tabular-nums text-gray-500 dark:text-gray-400">{a.tender_count}</span>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {/* Top Contractors */}
      <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Top Contractors
        </h2>
        {top_contractors.length === 0 ? (
          <p className="text-xs text-gray-400">No contractor data available.</p>
        ) : (
          <ul className="space-y-1.5">
            {top_contractors.slice(0, 5).map((c) => (
              <li key={c.contractor_name} className="flex items-center justify-between text-xs">
                <span className="truncate text-gray-700 dark:text-gray-300">{c.contractor_name}</span>
                <span className="ml-2 shrink-0 tabular-nums text-gray-500 dark:text-gray-400">
                  {c.win_rate_pct.toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function StatBlock({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-gray-50 p-2 dark:bg-gray-800/60">
      <Icon size={14} className="shrink-0 text-gray-400" />
      <div className="min-w-0">
        <p className="text-[10px] text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-sm font-semibold tabular-nums text-gray-900 dark:text-white">{value}</p>
      </div>
    </div>
  )
}

function MarketIntelSkeleton() {
  return (
    <div className="space-y-3">
      <div className="h-24 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
      <div className="h-20 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
      <div className="h-20 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
    </div>
  )
}
