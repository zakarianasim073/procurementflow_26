import { useQuery } from '@tanstack/react-query'
import { getContractorEligibility } from '@entities/contractor/api'

export function useEligibility(companyId?: string) {
  return useQuery({
    queryKey: ['contractor', companyId, 'eligibility'],
    queryFn: () => getContractorEligibility(companyId!),
    enabled: !!companyId,
    staleTime: 120_000,
  })
}
