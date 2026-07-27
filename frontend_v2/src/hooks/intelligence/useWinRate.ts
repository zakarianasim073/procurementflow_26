import { useQuery } from '@tanstack/react-query'
import { getWinRate } from '@entities/index'

export function useWinRate(agency?: string, limit?: number) {
  return useQuery({
    queryKey: ['intelligence', 'win-rate', agency, limit],
    queryFn: () => getWinRate(agency, limit),
    staleTime: 300_000,
    retry: 1,
  })
}
