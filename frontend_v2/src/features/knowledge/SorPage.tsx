import { useState } from 'react'
import { Search, Building2 } from 'lucide-react'
import { Card } from '@shared/ui/Card'
import { Input } from '@shared/ui/Input'
import { EmptyState } from '@shared/ui/EmptyState'
import { Skeleton } from '@shared/ui/Skeleton'
import { ScreenTemplate } from '@layouts/index'
import { useSorSearch, useSorAgencies } from '@hooks/index'

function SorRateCard({ rate }: { rate: any }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <span className="font-mono text-xs font-medium text-blue-600 dark:text-blue-400">{rate.code}</span>
          <p className="mt-1 text-sm text-gray-900 dark:text-white">{rate.description}</p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{rate.unit} · {rate.agency}</p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
          <span className="text-gray-500">Zone A</span>
          <p className="font-medium text-gray-900 dark:text-white">৳{rate.zone_a.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
          <span className="text-gray-500">Zone B</span>
          <p className="font-medium text-gray-900 dark:text-white">৳{rate.zone_b.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
          <span className="text-gray-500">Zone C</span>
          <p className="font-medium text-gray-900 dark:text-white">৳{rate.zone_c.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
          <span className="text-gray-500">Zone D</span>
          <p className="font-medium text-gray-900 dark:text-white">৳{rate.zone_d.toLocaleString()}</p>
        </div>
      </div>
    </Card>
  )
}

export function SorPage() {
  const [query, setQuery] = useState('')
  const [agency, setAgency] = useState('')

  const { data: searchResults, isLoading: searchLoading } = useSorSearch(query, agency || undefined)
  const { data: agencies, isLoading: agenciesLoading } = useSorAgencies()

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Schedule of Rates</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Browse and compare SOR rates across agencies</p>
        </div>
      }
      primary={
        <div className="space-y-6">
          {/* Agency Summary */}
          {agenciesLoading ? (
            <div className="grid grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
            </div>
          ) : agencies && (
            <div className="grid grid-cols-3 gap-4">
              {agencies.agencies.map((a: { name: string; total_rates: number }) => (
                <Card key={a.name} className="p-4">
                  <div className="flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-blue-500" />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{a.name}</h3>
                  </div>
                  <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">{a.total_rates}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">rates available</p>
                </Card>
              ))}
            </div>
          )}

          {/* Search */}
          <Card className="p-4">
            <div className="flex flex-wrap items-end gap-4">
              <Input
                label="Search SOR"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by code, description, or keyword"
                leftAddon={<Search className="h-4 w-4 text-gray-400" />}
                className="w-64"
              />
              <select
                value={agency}
                onChange={(e) => setAgency(e.target.value)}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
              >
                <option value="">All Agencies</option>
                <option value="BWDB">BWDB</option>
                <option value="PWD">PWD</option>
                <option value="LGED">LGED</option>
              </select>
            </div>
          </Card>

          {/* Results */}
          {searchLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
            </div>
          ) : !query ? (
            <EmptyState
              title="Search SOR rates"
              description="Enter a code or keyword to search the Schedule of Rates database."
            />
          ) : !searchResults?.rates.length ? (
            <EmptyState
              title="No results found"
              description="Try a different search term or filter."
            />
          ) : (
            <div>
              <p className="mb-3 text-sm text-gray-500 dark:text-gray-400">{searchResults.total_count} results</p>
              <div className="space-y-3">
                {searchResults.rates.map((rate) => (
                  <SorRateCard key={`${rate.agency}-${rate.code}`} rate={rate} />
                ))}
              </div>
            </div>
          )}
        </div>
      }
    />
  )
}
