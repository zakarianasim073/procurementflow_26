import { useSearchParams } from 'react-router-dom'
import type { DiscoveryFilters } from './FilterBar'

export function useDiscoveryFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  const filters: DiscoveryFilters = {
    query: searchParams.get('q') ?? '',
    agency: searchParams.get('agency') ?? 'All',
    status: searchParams.get('status') ?? 'All',
    dateRange: searchParams.get('range') ?? 'All',
    min_value: searchParams.get('min') ?? '',
    max_value: searchParams.get('max') ?? '',
  }

  function setFilter(key: keyof DiscoveryFilters, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value && value !== 'All') {
        const paramKey = key === 'query' ? 'q' : key === 'dateRange' ? 'range' : (key as string)
        next.set(paramKey, value)
      } else {
        const paramKey = key === 'query' ? 'q' : key === 'dateRange' ? 'range' : (key as string)
        next.delete(paramKey)
      }
      return next
    })
  }

  function clearFilters() {
    setSearchParams(new URLSearchParams())
  }

  const hasActiveFilters = Object.entries(filters).some(([key, val]) => {
    if (key === 'query') return val !== ''
    if (key === 'min_value' || key === 'max_value') return val !== ''
    return val !== 'All'
  })

  return { filters, setFilter, clearFilters, hasActiveFilters }
}
