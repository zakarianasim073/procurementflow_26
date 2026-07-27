import { useQuery } from '@tanstack/react-query'
import { searchClauses } from '@entities/index'

export function useClauseSearch(q: string) {
  return useQuery({
    queryKey: ['clauses', 'search', q],
    queryFn: () => searchClauses(q),
    staleTime: 60_000,
    retry: 1,
    enabled: q.length > 0,
  })
}
