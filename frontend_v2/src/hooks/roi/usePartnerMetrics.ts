import { useQuery } from '@tanstack/react-query'
import { getPartnerMetrics } from '@entities/roi/api'

export function usePartnerMetrics(companyId?: string) {
  return useQuery({
    queryKey: ['partnerMetrics', companyId],
    queryFn: () => getPartnerMetrics(companyId!),
    enabled: !!companyId,
    staleTime: 120_000,
  })
}
