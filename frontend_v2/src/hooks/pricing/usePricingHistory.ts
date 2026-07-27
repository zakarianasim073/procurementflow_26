import { useQuery } from '@tanstack/react-query'
import { getPricingHistory } from '@entities/pricing/api'

export function usePricingHistory(tenderId?: string) {
  return useQuery({
    queryKey: ['pricingHistory', tenderId],
    queryFn: () => getPricingHistory(tenderId!),
    enabled: !!tenderId,
    staleTime: 60_000,
  })
}
