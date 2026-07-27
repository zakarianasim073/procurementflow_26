import { Users, FileText } from 'lucide-react'
import type { OpeningReportItem } from '@entities/index'

interface OpeningReportsProps {
  items: OpeningReportItem[]
  isLoading?: boolean
}

function formatDate(d: string): string {
  try { return new Date(d).toLocaleDateString() } catch { return d }
}

export function OpeningReports({ items, isLoading }: OpeningReportsProps) {
  if (isLoading) {
    return <div className="h-40 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 text-center dark:border-gray-800 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">No opening reports yet.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Recent Opening Reports</h2>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {items.map((r) => (
          <div key={r.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
            <FileText size={14} className="shrink-0 text-gray-400" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-gray-500">{r.tender_id}</span>
                <span className="text-xs text-gray-400">{r.agency}</span>
              </div>
              <p className="truncate text-xs text-gray-500 dark:text-gray-400">{r.pe_office}</p>
            </div>
            <div className="flex shrink-0 items-center gap-2 text-xs text-gray-400">
              <Users size={12} />
              <span>{r.bidders_count}</span>
              <span>{formatDate(r.opening_date)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
