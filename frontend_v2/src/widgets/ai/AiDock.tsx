import { useState, useRef, useEffect } from 'react'
import { Bot, X, MessageSquare } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { PromptBox } from '@widgets/ai/PromptBox'
import { ThinkingIndicator } from '@widgets/ai/ThinkingIndicator'
import { TrustPanel } from '@widgets/ai/TrustPanel'

interface DockMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  confidence?: string
  evidenceScore?: number
  timestamp: Date
}

interface AiDockProps {
  isOpen: boolean
  onClose: () => void
  context?: {
    tenderId?: string
    workspace?: string
    section?: string
  }
}

export function AiDock({ isOpen, onClose, context }: AiDockProps) {
  const [messages, setMessages] = useState<DockMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend(content: string) {
    const userMessage: DockMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    // Simulate AI response
    setTimeout(() => {
      const aiMessage: DockMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: `I'll help you with that. ${context?.tenderId ? `Working on tender ${context.tenderId}.` : 'No specific tender context loaded.'}`,
        confidence: 'Medium',
        evidenceScore: 0.75,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, aiMessage])
      setIsLoading(false)
    }, 1500)
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900 sm:max-w-lg"
      role="dialog"
      aria-label="AI Copilot Dock"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-blue-500" />
          <span className="font-semibold text-gray-900 dark:text-white">AI Copilot</span>
          {context?.tenderId && (
            <span className="rounded bg-blue-100 px-2 py-0.5 font-mono text-xs text-blue-700 dark:bg-blue-900 dark:text-blue-300">
              {context.tenderId}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
          aria-label="Close AI Dock"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <MessageSquare className="mb-3 h-12 w-12 text-gray-300 dark:text-gray-600" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Ask me anything about this tender or workspace.
            </p>
          </div>
        )}

        <div className="space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'rounded-xl p-3',
                msg.role === 'user'
                  ? 'ml-8 bg-blue-50 dark:bg-blue-900/20'
                  : 'mr-8 bg-gray-50 dark:bg-gray-800'
              )}
            >
              <div className="flex items-start justify-between">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {msg.role === 'user' ? 'You' : 'AI'}
                </span>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {msg.timestamp.toLocaleTimeString()}
                </span>
              </div>
              <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{msg.content}</p>
              {msg.confidence && (
                <TrustPanel confidence={Number(msg.confidence)} verdict="passed">
                  <span className="text-xs text-gray-400">Grounded in tender analysis</span>
                </TrustPanel>
              )}
            </div>
          ))}

          {isLoading && <ThinkingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4 dark:border-gray-800">
        <PromptBox
          onSubmit={handleSend}
          disabled={isLoading}
          placeholder="Ask about this tender..."
        />
      </div>
    </div>
  )
}

export function AiDockTrigger({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
      aria-label="Open AI Copilot"
    >
      <Bot className="h-6 w-6" />
    </button>
  )
}
