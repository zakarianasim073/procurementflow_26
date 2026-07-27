import { useQuery } from '@tanstack/react-query'
import { getFeedbackForTender } from '@entities/feedback/api'

export function useFeedbackForTender(tenderId?: string) {
  return useQuery({
    queryKey: ['feedback', 'tender', tenderId],
    queryFn: () => getFeedbackForTender(tenderId!),
    enabled: !!tenderId,
    staleTime: 60_000,
    retry: 1,
  })
}
