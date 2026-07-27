import { useState, useEffect, useCallback, useRef } from 'react'

export interface WidgetState<T> {
  data: T[]
  loading: boolean
  error: string | null
  filters: Record<string, string>
  activeTab: string
  activeSubTab: string
}

export interface WidgetActions {
  setFilter: (key: string, value: string) => void
  setActiveTab: (tab: string) => void
  setActiveSubTab: (subTab: string) => void
  refresh: () => void
  search: (query: string) => void
}

export function useWidgetData<T>(
  fetchFn: () => Promise<T[]>,
  options?: { initialTab?: string; initialSubTab?: string },
): WidgetState<T> & WidgetActions {
  const [data, setData] = useState<T[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [activeTab, setActiveTab] = useState(options?.initialTab ?? 'all')
  const [activeSubTab, setActiveSubTab] = useState(options?.initialSubTab ?? 'all')
  const refreshKey = useRef(0)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchFn()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [fetchFn])

  useEffect(() => {
    load()
  }, [load])

  const setFilter = useCallback((key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }, [])

  const refresh = useCallback(() => {
    refreshKey.current++
    load()
  }, [load])

  const search = useCallback((query: string) => {
    setFilter('search', query)
  }, [setFilter])

  return {
    data, loading, error, filters,
    activeTab, activeSubTab,
    setFilter, setActiveTab, setActiveSubTab, refresh, search,
  }
}
