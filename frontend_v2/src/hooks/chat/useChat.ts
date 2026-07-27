import { useMutation, useQuery } from '@tanstack/react-query'
import { sendChatMessage, getChatModels } from '@entities/index'
import type { ChatMessage } from '@entities/index'

export function useChatModels() {
  return useQuery({
    queryKey: ['chat', 'models'],
    queryFn: () => getChatModels(),
    staleTime: 300_000,
  })
}

export function useSendMessage() {
  return useMutation({
    mutationFn: (messages: ChatMessage[]) =>
      sendChatMessage({ messages, engine: 'auto', language: 'en' }),
  })
}
