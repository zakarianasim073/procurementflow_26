import { Shield } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { ConfidenceMeter } from '@widgets/ai/ConfidenceMeter'

export interface EvidenceCardProps {
  id: string
  title: string
  source: string
  confidence?: number
  excerpt?: string
  createdAt?: string
  onClick?: () => void
  className?: string
}

export function EvidenceCard({ title, source, confidence, excerpt, createdAt, onClick, className }: EvidenceCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full rounded-xl border border-gray-200 bg-white p-4 text-left transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-900',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        className,
      )}
    >
      <div className="flex items-start gap-2">
        <Shield size={14} className="mt-0.5 shrink-0 text-brand-600 dark:text-brand-400" />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">{source}</p>
        </div>
      </div>
      {excerpt && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-2 italic">&ldquo;{excerpt}&rdquo;</p>
      )}
      {confidence != null && (
        <div className="mt-3">
          <ConfidenceMeter value={confidence} label="Confidence" size="sm" />
        </div>
      )}
      {createdAt && (
        <time className="mt-2 block text-[10px] text-gray-400 dark:text-gray-500">
          {new Date(createdAt).toLocaleDateString()}
        </time>
      )}
    </button>
  )
}
