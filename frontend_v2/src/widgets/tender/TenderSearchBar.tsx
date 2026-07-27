import { Search, X } from 'lucide-react'
import { useAgencies } from '@hooks/opportunity'

const FALLBACK_AGENCIES = [
  { value: '', label: 'All Agencies' },
  { value: 'BWDB', label: 'BWDB' },
  { value: 'PWD', label: 'PWD' },
  { value: 'LGED', label: 'LGED' },
  { value: 'RHD', label: 'RHD' },
]

interface TenderSearchBarProps {
  query: string
  agency: string
  onQueryChange: (q: string) => void
  onAgencyChange: (a: string) => void
}

export function TenderSearchBar({ query, agency, onQueryChange, onAgencyChange }: TenderSearchBarProps) {
  const { data: agenciesData } = useAgencies()

  const agencyOptions = agenciesData?.agencies?.length
    ? [{ value: '', label: 'All Agencies' }, ...agenciesData.agencies.map((a) => ({ value: a.id.toUpperCase(), label: a.name }))]
    : FALLBACK_AGENCIES

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative flex-1">
        <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search across 395,000+ tenders..."
          aria-label="Search tenders"
          className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-8 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-blue-500 dark:focus:ring-blue-900/50"
        />
        {query && (
          <button
            onClick={() => onQueryChange('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Clear search"
          >
            <X size={14} />
          </button>
        )}
      </div>

      <select
        value={agency}
        onChange={(e) => onAgencyChange(e.target.value)}
        aria-label="Filter by agency"
        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:focus:border-blue-500 dark:focus:ring-blue-900/50"
      >
        {agencyOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}
