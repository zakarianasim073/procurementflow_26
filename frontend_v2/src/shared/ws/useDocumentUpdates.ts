import { useQueryClient } from '@tanstack/react-query'
import { useWebSocket, type WebSocketMessage } from './useWebSocket'

export interface DocumentUpdateMessage {
  document_id: string
  extraction_status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: number
  data?: Record<string, unknown>
  error?: string
}

export function useDocumentUpdates(enabled: boolean = true) {
  const queryClient = useQueryClient()

  const handleMessage = (msg: WebSocketMessage) => {
    if (msg.type === 'document_update') {
      const update = msg.data as unknown as DocumentUpdateMessage

      // Update document queries with new status
      queryClient.invalidateQueries({ queryKey: ['documents'] })

      // If completed, trigger refetch
      if (update.extraction_status === 'completed') {
        queryClient.invalidateQueries({ queryKey: ['document', update.document_id] })
      }
    }
  }

  const { connected, error } = useWebSocket('/documents', enabled ? handleMessage : undefined)

  return { connected, error }
}
