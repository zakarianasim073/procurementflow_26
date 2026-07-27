export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface ChatRequest {
  messages: ChatMessage[]
  language?: 'en' | 'bn'
  engine?: 'auto' | 'ollama' | 'openai' | 'anthropic'
}

export interface ChatResponse {
  success: boolean
  content: string
  tokens_used: number
  engine: string
}

export interface ChatModel {
  id: string
  name: string
  provider: string
  available: boolean
}
