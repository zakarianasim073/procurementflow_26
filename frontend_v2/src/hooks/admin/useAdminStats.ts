import { useQuery } from '@tanstack/react-query'
import { getAdminStats } from '@entities/admin'

export function useAdminStats() {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: queryFn,
    staleTime: 60_000,
    retry: 1,
  })

  function queryFn() {
    return getAdminStats();
  }
}
