import { useState } from 'react'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { useIntelCatalogue, useIntelDataset } from '@hooks/index'

const CARD = 'rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900'
const TH = 'px-3 py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400 whitespace-nowrap'
const TD = 'px-3 py-2 text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap max-w-[18rem] truncate'

function fmt(v: unknown): string {
  if (v == null) return '—'
  if (typeof v === 'number') return v.toLocaleString()
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

export function IntelligenceExplorer() {
  const cat = useIntelCatalogue()
  const [dataset, setDataset] = useState('works_contractors')
  const [q, setQ] = useState('')
  const page = useIntelDataset(dataset, 50, 0, q || undefined)

  const rows = page.data?.rows ?? []
  // Column set = union of keys from the first few rows, key_id first.
  const cols = rows.length
    ? Array.from(new Set(rows.slice(0, 8).flatMap(r => Object.keys(r))))
        .sort((a, b) => (a === 'key_id' ? -1 : b === 'key_id' ? 1 : 0))
        .slice(0, 12)
    : []

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Intelligence Explorer</h1>
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
            {cat.data?.length ?? 0} certified Works datasets · {(cat.data?.reduce((s, d) => s + d.rows, 0) ?? 0).toLocaleString()} rows
          </p>
        </div>
      }
      primary={
        <div className="space-y-4">
          <div className={CARD}>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={dataset}
                onChange={e => setDataset(e.target.value)}
                className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              >
                {(cat.data ?? []).map(d => (
                  <option key={d.dataset} value={d.dataset}>
                    {d.dataset} ({d.rows.toLocaleString()})
                  </option>
                ))}
              </select>
              <input
                value={q}
                onChange={e => setQ(e.target.value)}
                placeholder="filter by key (contractor / tender / agency)…"
                className="flex-1 min-w-[12rem] rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
          </div>

          <div className={CARD}>
            {page.isLoading ? (
              <Skeleton className="h-64 w-full rounded-lg" />
            ) : !rows.length ? (
              <EmptyState title="No rows" description="This dataset returned no records for the current filter." />
            ) : (
              <>
                <p className="mb-2 text-xs text-gray-500 dark:text-gray-400">
                  {page.data?.total.toLocaleString()} rows · showing {rows.length}
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b border-gray-200 dark:border-gray-800">
                      <tr>{cols.map(c => <th key={c} className={TH}>{c}</th>)}</tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                      {rows.map((r, i) => (
                        <tr key={i}>
                          {cols.map(c => (
                            <td key={c} className={`${TD} ${typeof r[c] === 'number' ? 'tabular-nums' : ''}`} title={fmt(r[c])}>
                              {fmt(r[c])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </div>
      }
    />
  )
}
