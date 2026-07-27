import { useQuery } from '@tanstack/react-query'
import { getContractorExperience } from '@entities/contractor/api'

export function useExperience(companyId?: string) {
  return useQuery({
    queryKey: ['contractor', companyId, 'experience'],
    queryFn: () => getContractorExperience(companyId!),
    enabled: !!companyId,
    staleTime: 120_000,
  })
}
