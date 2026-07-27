import { useQuery } from '@tanstack/react-query'
import { getContractorRisk } from '@entities/contractor/api'

export function useRiskProfile(companyId?: string) {
  return useQuery({
    queryKey: ['contractor', companyId, 'risk'],
    queryFn: () => getContractorRisk(companyId!),
    enabled: !!companyId,
    staleTime: 120_000,
  })
}
