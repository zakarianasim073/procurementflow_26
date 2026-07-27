import { cn } from '@shared/lib/cn'
import { Bot, Scale } from 'lucide-react'

interface WidgetActionsProps {
  onAiAction?: () => void
  onEvidence?: () => void
  aiLabel?: string
  evidenceLabel?: string
  className?: string
}

export function WidgetActions({ onAiAction, onEvidence, aiLabel = 'AI', evidenceLabel = 'Evidence', className }: WidgetActionsProps) {
  return (
    <div className={cn('flex items-center gap-1 border-t border-gray-50 bg-gray-50/50 px-4 py-1.5 dark:border-gray-800 dark:bg-gray-800/20', className)}>
      {onAiAction && (
        <button
          type="button"
          onClick={onAiAction}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-brand-600 hover:bg-brand-50 dark:text-brand-400 dark:hover:bg-brand-900/10 transition-colors"
        >
          <Bot size={12} />
          {aiLabel}
        </button>
      )}
      {onEvidence && (
        <button
          type="button"
          onClick={onEvidence}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 transition-colors"
        >
          <Scale size={12} />
          {evidenceLabel}
        </button>
      )}
    </div>
  )
}
