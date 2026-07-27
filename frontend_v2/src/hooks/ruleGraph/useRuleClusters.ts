import { useQuery } from '@tanstack/react-query'
import { getRuleClusters } from '@entities/index'

export function useRuleClusters() {
  return useQuery({
    queryKey: ['ruleClusters'],
    queryFn: () => getRuleClusters(),
    staleTime: 300_000,
    retry: 1,
  })
}
