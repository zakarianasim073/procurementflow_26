import { useQuery } from '@tanstack/react-query'
import { getPricingPrediction, type PricingPredictionParams } from '@entities/pricing/api'

export function usePricingPrediction(tenderId?: string, params?: PricingPredictionParams) {
  return useQuery({
    queryKey: ['pricingPrediction', tenderId, params],
    queryFn: () => getPricingPrediction(tenderId!, params!),
    // bid_price / estimated_cost / bidder_count are all required by the API;
    // without them the request 422s, so don't fire until they're present.
    enabled:
      !!tenderId &&
      params != null &&
      params.bid_price != null &&
      params.estimated_cost != null &&
      params.bidder_count != null,
    staleTime: 30_000,
  })
}
