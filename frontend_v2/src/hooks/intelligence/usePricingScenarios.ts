import { useQuery } from '@tanstack/react-query'
import { getPricingScenarios } from '@entities/index'

export function usePricingScenarios() {
  return useQuery({
    queryKey: ['intelligence', 'pricing-scenarios'],
    queryFn: getPricingScenarios,
    staleTime: 300_000,
    retry: 1,
  })
}
