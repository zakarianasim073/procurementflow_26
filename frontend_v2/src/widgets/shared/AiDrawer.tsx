import { useState } from 'react'
import { cn } from '@shared/lib/cn'
import { X, Bot, Sparkles, Send, MessageSquare, FileText, TrendingUp, Shield } from 'lucide-react'
import { Badge } from '@shared/ui/Badge'

interface AiDrawerProps {
  open: boolean
  onClose: () => void
  widgetTitle?: string
}

const QUICK_ACTIONS = [
  { label: 'Analyze', icon: Bot },
  { label: 'Explain', icon: MessageSquare },
  { label: 'Compare', icon: FileText },
  { label: 'Predict', icon: TrendingUp },
  { label: 'Verify', icon: Shield },
]

export function AiDrawer({ open, onClose, widgetTitle }: AiDrawerProps) {
  const [query, setQuery] = useState('')

  return (
    <div
      className={cn(
        'fixed inset-y-0 right-0 z-50 w-full max-w-md transform border-l border-gray-200 bg-white shadow-2xl transition-transform duration-300 dark:border-gray-800 dark:bg-gray-900',
        open ? 'translate-x-0' : 'translate-x-full',
      )}
    >
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <Bot size={16} className="text-brand-500" />
            <span className="text-sm font-semibold text-gray-900 dark:text-white">AI Assistant</span>
            {widgetTitle && <Badge variant="outline" className="text-[10px]">{widgetTitle}</Badge>}
          </div>
          <button type="button" onClick={onClose} className="rounded-md p-1 hover:bg-gray-100 dark:hover:bg-gray-800">
            <X size={16} className="text-gray-500" />
          </button>
        </div>

        <div className="flex gap-1 border-b border-gray-100 px-4 py-2 dark:border-gray-800">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon
            return (
              <button
                key={action.label}
                type="button"
                className="flex items-center gap-1 rounded-md px-2.5 py-1.5 text-[11px] font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white transition-colors"
              >
                <Icon size={12} />
                {action.label}
              </button>
            )
          })}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <div className="rounded-lg border border-brand-100 bg-brand-50/50 p-3 dark:border-brand-900/20 dark:bg-brand-900/10">
              <div className="flex items-center gap-1.5 mb-1">
                <Sparkles size={12} className="text-brand-500" />
                <span className="text-[11px] font-medium text-brand-700 dark:text-brand-400">AI Suggestion</span>
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                I can help analyze this widget's data, explain trends, generate reports, or predict outcomes based on historical patterns.
              </p>
            </div>

            <div className="space-y-2">
              <p className="text-[11px] font-medium text-gray-500">Suggested actions for this widget</p>
              {[
                'Summarize key metrics and trends',
                'Identify anomalies in the data',
                'Compare with previous period',
                'Generate exportable report',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="w-full text-left rounded-md px-3 py-2 text-xs text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="border-t border-gray-100 p-3 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask AI about this widget..."
              className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs placeholder-gray-400 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
            />
            <button type="button" className="rounded-md bg-brand-500 p-2 text-white hover:bg-brand-600 transition-colors">
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
