import { fetchJson } from '../sharedApi'
import type { ChatRequest, ChatResponse, ChatModel } from './types'

export function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  return fetchJson<ChatResponse>('/api/v2', {
    method: 'POST',
    body: JSON.stringify(req),
    authed: true,
  })
}

export function getChatModels(): Promise<ChatModel[]> {
  return fetchJson<ChatModel[]>('/api/v2/models', true)
}
