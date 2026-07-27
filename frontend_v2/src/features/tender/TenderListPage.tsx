import { useState, useEffect, useRef } from 'react'
import { ScreenTemplate } from '@layouts/index'
import { useTenderSearch } from '@hooks/index'
import { TenderSearchBar, TenderResultTable, TenderResultTableSkeleton } from '@widgets/index'

const PAGE_SIZE = 50

export function TenderListPage() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [agency, setAgency] = useState('')
  const [offset, setOffset] = useState(0)
  const [scope, setScope] = useState<'live' | 'all'>('live')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(query)
      setOffset(0)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query])

  const { data, isLoading } = useTenderSearch({
    q: debouncedQuery,
    agency: agency || undefined,
    limit: PAGE_SIZE,
    offset,
    scope,
  })

  const results = data?.data ?? []
  const total = data?.count ?? 0
  const hasMore = data?.has_more ?? false

  return (
    <ScreenTemplate
      header={
        <>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Tender Workspace</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {scope === 'live'
              ? `Browse ${total.toLocaleString()} current Works tenders from the national e-GP feed`
              : 'Search the 395,000+ tender PG17 archive'}
          </p>
        </>
      }
      primary={
        <div className="space-y-3">
          <TenderSearchBar
            query={query}
            agency={agency}
            onQueryChange={(q) => { setQuery(q); setOffset(0) }}
            onAgencyChange={(a) => { setAgency(a); setOffset(0) }}
          />
          <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-900">
            <button type="button" onClick={() => { setScope('live'); setOffset(0) }} className={`rounded-md px-3 py-1.5 text-sm font-medium ${scope === 'live' ? 'bg-blue-600 text-white' : 'text-gray-600 dark:text-gray-300'}`}>Live e-GP Works</button>
            <button type="button" onClick={() => { setScope('all'); setOffset(0) }} className={`rounded-md px-3 py-1.5 text-sm font-medium ${scope === 'all' ? 'bg-blue-600 text-white' : 'text-gray-600 dark:text-gray-300'}`}>PG17 Archive</button>
          </div>

          {(scope === 'all' && !debouncedQuery && !agency) ? (
            <div className="rounded-xl border border-gray-200 bg-white p-8 text-center dark:border-gray-800 dark:bg-gray-900">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Search across 395,000+ archived tenders. Enter a keyword to begin.
              </p>
            </div>
          ) : isLoading ? (
            <TenderResultTableSkeleton />
          ) : (
            <TenderResultTable
              data={results}
              total={total}
              offset={offset}
              limit={PAGE_SIZE}
              hasMore={hasMore}
              isLoading={isLoading}
              onPrevPage={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              onNextPage={() => setOffset(offset + PAGE_SIZE)}
            />
          )}
        </div>
      }
    />
  )
}
