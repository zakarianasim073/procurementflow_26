import { useQuery } from '@tanstack/react-query'
import { getContractorOpportunities } from '@entities/contractor/api'

export function useOpportunities(companyId?: string) {
  return useQuery({
    queryKey: ['contractor', companyId, 'opportunities'],
    queryFn: () => getContractorOpportunities(companyId!),
    enabled: !!companyId,
    staleTime: 120_000,
  })
}
