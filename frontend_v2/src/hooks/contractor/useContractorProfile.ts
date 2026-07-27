import { useQuery } from '@tanstack/react-query'
import { getContractorProfile } from '@entities/contractor/api'

export function useContractorProfile(companyId?: string) {
  return useQuery({
    queryKey: ['contractor', companyId, 'profile'],
    queryFn: () => getContractorProfile(companyId!),
    enabled: !!companyId,
    staleTime: 120_000,
  })
}
