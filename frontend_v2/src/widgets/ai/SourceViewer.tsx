import { FileText, ExternalLink } from 'lucide-react'
import { cn } from '@shared/lib/cn'

export interface SourceDocument {
  id: string
  name: string
  type?: string
  url?: string
  excerpt?: string
}

export interface SourceViewerProps {
  sources: SourceDocument[]
  className?: string
}

export function SourceViewer({ sources, className }: SourceViewerProps) {
  if (sources.length === 0) {
    return (
      <div className={cn('rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900', className)}>
        <p className="text-xs text-gray-500 dark:text-gray-400">No sources cited.</p>
      </div>
    )
  }

  return (
    <div className={cn('rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900', className)}>
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Sources</p>
      <div className="space-y-2">
        {sources.map((source) => (
          <div key={source.id} className="flex items-start gap-2">
            <FileText size={14} className="mt-0.5 shrink-0 text-gray-400 dark:text-gray-500" />
            <div className="min-w-0 flex-1">
              {source.url ? (
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
                >
                  <span className="truncate">{source.name}</span>
                  <ExternalLink size={10} className="shrink-0" />
                </a>
              ) : (
                <span className="text-xs font-medium text-gray-900 dark:text-white">{source.name}</span>
              )}
              {source.type && (
                <span className="ml-1 text-[10px] text-gray-400 dark:text-gray-500">({source.type})</span>
              )}
              {source.excerpt && (
                <p className="mt-0.5 text-[11px] text-gray-500 dark:text-gray-400 line-clamp-2 italic">
                  &ldquo;{source.excerpt}&rdquo;
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
