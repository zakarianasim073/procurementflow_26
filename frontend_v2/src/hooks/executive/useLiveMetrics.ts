import { useQuery } from '@tanstack/react-query'
import { getLiveMetrics } from '@entities/index'

export function useLiveMetrics() {
  return useQuery({
    queryKey: ['analytics', 'live-metrics'],
    queryFn: getLiveMetrics,
    staleTime: 60_000,
    retry: 2,
  })
}
