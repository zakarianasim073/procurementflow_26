import { useMutation } from '@tanstack/react-query'
import { submitFeedback } from '@entities/feedback/api'
import type { FeedbackSubmitPayload } from '@entities/feedback/types'

export function useSubmitFeedback() {
  return useMutation({
    mutationFn: (data: FeedbackSubmitPayload) => submitFeedback(data),
    onSuccess: () => {
      // Invalidate feedback queries so they refetch after new submission
      // queryClient.invalidateQueries({ queryKey: ['feedback'] })
    },
  })
}
