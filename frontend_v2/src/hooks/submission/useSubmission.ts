import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSubmissions, getSubmissionTimeline, updateSubmissionStatus } from '@entities/submission'

export function useSubmissions(tenderId?: string) {
  return useQuery({
    queryKey: ['submissions', tenderId],
    queryFn: () => getSubmissions(tenderId),
    staleTime: 60_000,
  })
}

export function useSubmissionTimeline(submissionId: string) {
  return useQuery({
    queryKey: ['submissions', 'timeline', submissionId],
    queryFn: () => getSubmissionTimeline(submissionId),
    staleTime: 60_000,
    enabled: !!submissionId,
  })
}

export function useUpdateSubmissionStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ submissionId, status }: { submissionId: string; status: string }) =>
      updateSubmissionStatus(submissionId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] })
    },
  })
}
