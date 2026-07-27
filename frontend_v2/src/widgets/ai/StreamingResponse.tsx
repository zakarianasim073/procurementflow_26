import { useEffect, useRef } from 'react'
import { cn } from '@shared/lib/cn'

export interface StreamingResponseProps {
  content: string
  isStreaming?: boolean
  className?: string
}

export function StreamingResponse({ content, isStreaming, className }: StreamingResponseProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [content])

  if (!content && !isStreaming) return null

  return (
    <div
      ref={containerRef}
      className={cn(
        'max-h-96 overflow-y-auto rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900',
        className,
      )}
      aria-live="polite"
      aria-label="AI response"
    >
      <div className="prose prose-sm dark:prose-invert max-w-none text-sm text-gray-700 dark:text-gray-300">
        {content.split('\n').map((line, i) => (
          <p key={i} className={cn(!line && 'h-4')}>
            {line || '\u00A0'}
          </p>
        ))}
      </div>
      {isStreaming && (
        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-brand-600 dark:bg-brand-400" aria-hidden="true" />
      )}
    </div>
  )
}
