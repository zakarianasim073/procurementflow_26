import { useQuery } from '@tanstack/react-query'
import { getPricingStrategy } from '@entities/pricing/api'

export function usePricingStrategy(tenderId?: string, strategyId?: string) {
  return useQuery({
    queryKey: ['pricingStrategy', tenderId, strategyId],
    queryFn: () => getPricingStrategy(tenderId!, strategyId!),
    enabled: !!tenderId && !!strategyId,
    staleTime: 120_000,
  })
}
