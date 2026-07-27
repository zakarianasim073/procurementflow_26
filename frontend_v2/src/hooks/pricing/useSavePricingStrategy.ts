import { useMutation, useQueryClient } from '@tanstack/react-query'
import { savePricingStrategy } from '@entities/pricing/api'

export function useSavePricingStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { tenderId: string; strategy: { name: string; discount_percent: number; bid_price: number; rationale: string } }) => savePricingStrategy(data.tenderId, data.strategy),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pricingStrategy', variables.tenderId] })
    },
  })
}
