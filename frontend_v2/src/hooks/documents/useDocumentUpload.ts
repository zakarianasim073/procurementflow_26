import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadDocument } from '@entities/documents'

export function useDocumentUpload() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: { tenderId: string; file: File; docType: string }) =>
      uploadDocument(payload.tenderId, payload.file, payload.docType),
    onSuccess: (_data) => {
      // Invalidate document list queries
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })
}
