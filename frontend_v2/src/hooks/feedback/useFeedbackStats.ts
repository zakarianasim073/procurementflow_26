import { useQuery } from '@tanstack/react-query'
import { getFeedbackStats } from '@entities/feedback/api'

export function useFeedbackStats(period?: 'all' | '30d' | '90d') {
  return useQuery({
    queryKey: ['feedback', 'stats', period],
    queryFn: () => getFeedbackStats(),
    staleTime: 120_000,
    retry: 1,
  })
}
