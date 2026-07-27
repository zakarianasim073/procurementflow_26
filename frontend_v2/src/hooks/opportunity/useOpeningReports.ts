import { useQuery } from '@tanstack/react-query'
import { getOpeningReports } from '@entities/index'

export function useOpeningReports(limit = 10) {
  return useQuery({
    queryKey: ['opportunity', 'opening-reports', limit],
    queryFn: () => getOpeningReports(limit),
    staleTime: 60_000,
    retry: 1,
  })
}
