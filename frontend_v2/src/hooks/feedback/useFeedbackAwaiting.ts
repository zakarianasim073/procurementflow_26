import { useQuery } from '@tanstack/react-query'
import { getFeedbackAwaiting } from '@entities/feedback/api'

export function useFeedbackAwaiting() {
  return useQuery({
    queryKey: ['feedback', 'awaiting'],
    queryFn: getFeedbackAwaiting,
    staleTime: 30_000,
    retry: 1,
  })
}
