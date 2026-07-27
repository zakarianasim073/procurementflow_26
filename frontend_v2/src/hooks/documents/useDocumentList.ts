import { useQuery } from '@tanstack/react-query'
import { listDocuments } from '@entities/documents'
import type { DocumentListParams } from '@entities/documents'

export function useDocumentList(params: DocumentListParams) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: () => listDocuments(params),
    staleTime: 30_000,
    retry: 1,
    enabled: !!params.tender_id,
  })
}
