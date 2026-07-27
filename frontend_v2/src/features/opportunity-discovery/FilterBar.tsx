import { Search, X } from 'lucide-react'
import { Button } from '@shared/ui/Button'
import { Input } from '@shared/ui/Input'
import { useAgencies } from '@hooks/opportunity'

export interface DiscoveryFilters {
  query: string
  agency: string
  status: string
  dateRange: string
  min_value: string
  max_value: string
}

const FALLBACK_AGENCIES = ['All', 'BWDB', 'PWD', 'LGED', 'RHD', 'CDA']
const STATUSES = ['All', 'Live', 'Archive', 'Cancelled']
const DATE_RANGES = ['All', '7d', '30d', '90d']

interface FilterBarProps {
  filters: DiscoveryFilters
  onFilterChange: (key: keyof DiscoveryFilters, value: string) => void
  onClear: () => void
  hasActive: boolean
  resultCount?: number
}

export function FilterBar({ filters, onFilterChange, onClear, hasActive, resultCount }: FilterBarProps) {
  const { data: agenciesData } = useAgencies()

  const agencyOptions = agenciesData?.agencies?.length
    ? ['All', ...agenciesData.agencies.map((a) => a.id.toUpperCase())]
    : FALLBACK_AGENCIES

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <Input
          value={filters.query}
          onChange={(e) => onFilterChange('query', e.target.value)}
          placeholder="Search by title, package, agency…"
          className="pl-9"
        />
      </div>

      <select
        value={filters.agency}
        onChange={(e) => onFilterChange('agency', e.target.value)}
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white"
      >
        {agencyOptions.map((a) => (
          <option key={a} value={a}>{a === 'All' ? 'All Agencies' : a}</option>
        ))}
      </select>

      <select
        value={filters.status}
        onChange={(e) => onFilterChange('status', e.target.value)}
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white"
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>{s === 'All' ? 'All Statuses' : s}</option>
        ))}
      </select>

      <select
        value={filters.dateRange}
        onChange={(e) => onFilterChange('dateRange', e.target.value)}
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white"
      >
        {DATE_RANGES.map((d) => (
          <option key={d} value={d}>{d === 'All' ? 'Any Time' : d}</option>
        ))}
      </select>

      {resultCount !== undefined && (
        <span className="text-sm text-gray-500 dark:text-gray-400" aria-live="polite">
          {resultCount.toLocaleString()} tenders found
        </span>
      )}

      {hasActive && (
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="h-3 w-3 mr-1" />
          Clear
        </Button>
      )}
    </div>
  )
}
