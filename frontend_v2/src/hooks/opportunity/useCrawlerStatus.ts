import { useQuery } from '@tanstack/react-query'
import { getCrawlerStatus } from '@entities/index'

export function useCrawlerStatus() {
  return useQuery({
    queryKey: ['opportunity', 'crawler-status'],
    queryFn: getCrawlerStatus,
    staleTime: 15_000,
    retry: 1,
  })
}
