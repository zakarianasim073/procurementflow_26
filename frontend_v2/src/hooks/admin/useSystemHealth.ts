import { useQuery } from '@tanstack/react-query'
import { getSystemHealth } from '@entities/admin'

export function useSystemHealth() {
  return useQuery({
    queryKey: ['admin', 'health'],
    queryFn: () => getSystemHealth(),
    staleTime: 30_000,
    retry: 2,
  })
}
