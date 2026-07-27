import { useQuery } from '@tanstack/react-query'
import { getTenderDetail, getTenderBrainDetail } from '@entities/index'

export function useTenderDetail(tenderId: string) {
  return useQuery({
    queryKey: ['tender', 'detail', tenderId],
    queryFn: () => getTenderDetail(tenderId),
    staleTime: 60_000,
    retry: 1,
    enabled: !!tenderId,
  })
}

export function useTenderBrainDetail(tenderId: string) {
  return useQuery({
    queryKey: ['tender', 'brain', tenderId],
    queryFn: () => getTenderBrainDetail(tenderId),
    staleTime: 60_000,
    enabled: !!tenderId,
  })
}
