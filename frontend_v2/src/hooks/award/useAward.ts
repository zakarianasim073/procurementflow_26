import { useQuery } from '@tanstack/react-query'
import { getAwards, getAwardStats } from '@entities/award'

export function useAwards(params?: { procuring_entity?: string; contractor_name?: string; district?: string; work_type?: string; date_from?: string; date_to?: string; skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['awards', params],
    queryFn: () => getAwards(params),
    staleTime: 60_000,
  })
}

export function useAwardStats() {
  return useQuery({
    queryKey: ['awards', 'stats'],
    queryFn: () => getAwardStats(),
    staleTime: 60_000,
  })
}
