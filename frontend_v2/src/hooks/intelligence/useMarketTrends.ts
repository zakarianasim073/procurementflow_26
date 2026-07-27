import { useQuery } from '@tanstack/react-query'
import { getMarketTrends } from '@entities/index'

export function useMarketTrends(category?: string, zone?: string) {
  return useQuery({
    queryKey: ['intelligence', 'market-trends', category, zone],
    queryFn: () => getMarketTrends(category, zone),
    staleTime: 300_000,
    retry: 1,
  })
}
