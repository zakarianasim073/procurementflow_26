import { useQuery } from '@tanstack/react-query'
import { getCompetitors, getCompetitorAnalysis } from '@entities/competitor'

export function useCompetitors(params?: { district?: string; category?: string; search?: string; skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['competitors', params],
    queryFn: () => getCompetitors(params),
    staleTime: 60_000,
  })
}

export function useCompetitorAnalysis(tenderId: string) {
  return useQuery({
    queryKey: ['competitors', 'analysis', tenderId],
    queryFn: () => getCompetitorAnalysis(tenderId),
    staleTime: 60_000,
    enabled: !!tenderId,
  })
}
