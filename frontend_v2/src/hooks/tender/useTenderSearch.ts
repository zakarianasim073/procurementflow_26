import { useQuery } from '@tanstack/react-query'
import { searchTenders } from '@entities/index'
import type { TenderSearchParams } from '@entities/index'

export function useTenderSearch(params: TenderSearchParams) {
  return useQuery({
    queryKey: ['tender', 'search', params],
    queryFn: () => searchTenders(params),
    staleTime: 30_000,
    retry: 1,
  })
}
