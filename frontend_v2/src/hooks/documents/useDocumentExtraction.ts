import { useMutation, useQueryClient } from '@tanstack/react-query'
import { extractDocument } from '@entities/documents'

export function useDocumentExtraction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (documentId: string) => extractDocument(documentId),
    onSuccess: () => {
      // Invalidate document queries to refetch status
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })
}
