import { useQuery } from '@tanstack/react-query'
import { getExecutiveOverview } from '@entities/index'

export function useExecutiveOverview() {
  return useQuery({
    queryKey: ['executive', 'overview'],
    queryFn: getExecutiveOverview,
    staleTime: 60_000,
    retry: 2,
  })
}
