import { useState, useRef, useEffect } from 'react'
import { Bot, User, Loader2, AlertCircle } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { useChatModels, useSendMessage } from '@hooks/index'
import type { ChatMessage } from '@entities/index'
import { PromptBox } from '@widgets/ai/index'

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex items-start gap-3', isUser && 'flex-row-reverse')}>
      <div className={cn(
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
        isUser ? 'bg-blue-100 dark:bg-blue-900/40' : 'bg-gray-100 dark:bg-gray-800'
      )}>
        {isUser ? <User size={14} className="text-blue-600 dark:text-blue-400" /> : <Bot size={14} className="text-gray-600 dark:text-gray-400" />}
      </div>
      <div className={cn(
        'max-w-[80%] rounded-2xl px-4 py-2.5 text-sm',
        isUser ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
      )}>
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.timestamp && (
          <p className={cn('mt-1 text-[10px]', isUser ? 'text-blue-200' : 'text-gray-400')}>
            {new Date(message.timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  )
}

export function TrustChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Hello! I\'m your AI procurement assistant. How can I help you today?', timestamp: new Date().toISOString() },
  ])
  const chatEndRef = useRef<HTMLDivElement>(null)
  const models = useChatModels()
  const sendMessage = useSendMessage()

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return

    const userMsg: ChatMessage = { role: 'user', content: trimmed, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])

    try {
      const result = await sendMessage.mutateAsync([...messages, userMsg])
      const assistantMsg: ChatMessage = { role: 'assistant', content: result.content, timestamp: new Date().toISOString() }
      setMessages(prev => [...prev, assistantMsg])
    } catch {
      const errorMsg: ChatMessage = { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.', timestamp: new Date().toISOString() }
      setMessages(prev => [...prev, errorMsg])
    }
  }

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/40">
            <Bot size={16} className="text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">AI Assistant</h1>
            <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
              {models.isLoading ? 'Loading models...' : models.data && Array.isArray(models.data) ? `${models.data.filter(m => m.available).length} models available` : 'Chat mode'}
            </p>
          </div>
        </div>
      }
      primary={
        <div className="flex h-[calc(100vh-220px)] flex-col rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, i) => (
              <ChatBubble key={i} message={msg} />
            ))}
            {sendMessage.isPending && (
              <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
                  <Bot size={14} className="text-gray-600 dark:text-gray-400" />
                </div>
                <div className="flex items-center gap-2 rounded-2xl bg-gray-100 px-4 py-2.5 dark:bg-gray-800">
                  <Loader2 size={14} className="animate-spin text-gray-400" />
                  <span className="text-sm text-gray-500">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="border-t border-gray-200 p-3 dark:border-gray-700">
            {sendMessage.isError && (
              <div className="mb-2 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-950/30 dark:text-red-400">
                <AlertCircle size={12} /> Failed to send message. Check connection and try again.
              </div>
            )}
            <PromptBox onSubmit={handleSend} disabled={sendMessage.isPending} placeholder="Type your message..." />
          </div>
        </div>
      }
      aiDock={
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Available Models</h2>
          {models.isLoading ? (
            <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-10 w-full rounded-lg" />)}</div>
          ) : models.data && models.data.length > 0 ? (
            <div className="space-y-1.5">
              {models.data.map(m => (
                <div key={m.id} className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-800/60">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{m.name}</p>
                    <p className="text-[10px] text-gray-400">{m.provider}</p>
                  </div>
                  <span className={cn(
                    'h-2 w-2 rounded-full',
                    m.available ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
                  )} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400">No models available.</p>
          )}
        </div>
      }
    />
  )
}
