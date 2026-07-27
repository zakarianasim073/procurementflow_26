import { useQuery } from '@tanstack/react-query'
import { getClauses } from '@entities/index'

export function useClauses(params?: { schedule?: string; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['clauses', params],
    queryFn: () => getClauses(params),
    staleTime: 120_000,
    retry: 1,
  })
}
