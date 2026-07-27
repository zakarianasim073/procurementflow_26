import { useQuery } from '@tanstack/react-query'
import { getContractorAwards } from '@entities/contractor/api'

export function useAwards(companyId?: string, params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['contractor', companyId, 'awards', params],
    queryFn: () => getContractorAwards(companyId!, params),
    enabled: !!companyId,
    staleTime: 120_000,
  })
}
