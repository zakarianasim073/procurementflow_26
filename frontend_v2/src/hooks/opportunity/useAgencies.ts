import { useQuery } from '@tanstack/react-query'
import { getAgencies } from '@entities/index'

export function useAgencies() {
  return useQuery({
    queryKey: ['opportunity', 'agencies'],
    queryFn: getAgencies,
    staleTime: 120_000,
    retry: 1,
  })
}
