import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import type { TenderItem } from '@entities/index'

interface TenderResultTableProps {
  data: TenderItem[]
  total: number
  offset: number
  limit: number
  hasMore: boolean
  isLoading: boolean
  onPrevPage: () => void
  onNextPage: () => void
}

/**
 * Smallest figure treated as a real amount.
 *
 * Sub-rupee award values are crore-denominated at source and the API rescales
 * them to taka before they reach here. What remains below this floor is the
 * 10..1000 band, roughly 2.7k rows whose unit could not be established (their
 * ratio against a known-taka estimate is inconsistent), so they are shown as
 * unknown rather than rendered at a scale that may be wrong by 1e5.
 */
const MIN_MEANINGFUL_BDT = 1000

function formatCost(cost: number): string {
  const cr = cost / 1e7
  if (cr >= 1) return `${cr.toFixed(1)}Cr`
  const lakh = cost / 1e5
  if (lakh >= 1) return `${lakh.toFixed(0)}L`
  return `৳${Math.round(cost).toLocaleString()}`
}

/**
 * Pick the best available figure for a tender.
 *
 * About 29% of lifecycle rows carry no estimate, and a third of those do have a
 * final award amount. Falling back to it covers ~92% of rows instead of ~71%,
 * so the award value is shown and flagged rather than rendering a bare "0".
 */
function costDisplay(item: TenderItem): { text: string; isAward: boolean } | null {
  if (item.estimated_cost_bdt >= MIN_MEANINGFUL_BDT) {
    return { text: formatCost(item.estimated_cost_bdt), isAward: false }
  }
  if (item.award_amount_bdt != null && item.award_amount_bdt >= MIN_MEANINGFUL_BDT) {
    return { text: formatCost(item.award_amount_bdt), isAward: true }
  }
  return null
}

export function TenderResultTable({
  data,
  total,
  offset,
  limit,
  hasMore,
  isLoading,
  onPrevPage,
  onNextPage,
}: TenderResultTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-10 animate-pulse rounded bg-gray-100 dark:bg-gray-800/60" />
        ))}
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center dark:border-gray-800 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No results found. Try a different search term.
        </p>
      </div>
    )
  }

  const from = offset + 1
  const to = Math.min(offset + limit, total)

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500 dark:border-gray-800 dark:bg-gray-900/50 dark:text-gray-400">
            <tr>
              <th className="px-3 py-2.5 font-medium">Package</th>
              <th className="px-3 py-2.5 font-medium">Title</th>
              <th className="px-3 py-2.5 font-medium">Agency</th>
              <th className="px-3 py-2.5 font-medium">Zone</th>
              <th className="px-3 py-2.5 font-medium">Status / deadline</th>
              <th className="px-3 py-2.5 text-right font-medium">Security</th>
              <th
                className="px-3 py-2.5 text-right font-medium"
                title="Estimated cost, or the awarded amount (AWD) when no estimate was published"
              >
                Value
              </th>
              <th className="px-3 py-2.5 font-medium" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white dark:divide-gray-800 dark:bg-gray-900">
            {data.map((item) => (
              <tr
                key={item.tender_id}
                className="transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50"
              >
                <td className="px-3 py-2 font-mono text-xs text-gray-500 dark:text-gray-400">
                  {item.package_no}
                </td>
                <td className="max-w-sm truncate px-3 py-2 text-gray-900 dark:text-gray-100">
                  {item.title}
                </td>
                <td className="px-3 py-2">
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                    {item.agency_code}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">{item.zone_name}</td>
                <td className="whitespace-nowrap px-3 py-2 text-xs">
                  {item.source === 'egp_live' ? <><span className="rounded bg-green-100 px-1.5 py-0.5 font-medium text-green-700">LIVE</span><span className="ml-2 text-gray-500">{item.closing_date ? new Date(item.closing_date).toLocaleString() : '—'}</span></> : <span className="text-gray-500">Archive</span>}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-300">
                  {item.tender_security_text || (item.tender_security_amount_bdt ? formatCost(item.tender_security_amount_bdt) : '—')}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-700 dark:text-gray-300">
                  {(() => {
                    const cost = costDisplay(item)
                    if (!cost) return <span className="text-gray-400 dark:text-gray-600">—</span>
                    return (
                      <span title={cost.isAward ? 'Awarded amount (no estimate published)' : 'Estimated cost'}>
                        {cost.text}
                        {cost.isAward && (
                          <span className="ml-1 rounded bg-amber-50 px-1 text-[10px] font-medium text-amber-700 dark:bg-amber-500/10 dark:text-amber-500">
                            AWD
                          </span>
                        )}
                      </span>
                    )
                  })()}
                </td>
                <td className="px-3 py-2 text-right">
                  <Link
                    to={`/tender/${item.tender_id}`}
                    className="rounded p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                    title="View details"
                    aria-label={`View tender ${item.tender_id}`}
                  >
                    <ExternalLink size={14} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-900/50">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Showing {from}–{to} of {total.toLocaleString()}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={onPrevPage}
            disabled={offset === 0}
            className="rounded p-1 text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:hover:text-gray-500 dark:text-gray-400 dark:hover:text-gray-300"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={onNextPage}
            disabled={!hasMore}
            className="rounded p-1 text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:hover:text-gray-500 dark:text-gray-400 dark:hover:text-gray-300"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}

export function TenderResultTableSkeleton() {
  return (
    <div className="space-y-1">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-12 animate-pulse rounded bg-gray-100 dark:bg-gray-800/60" />
      ))}
    </div>
  )
}
