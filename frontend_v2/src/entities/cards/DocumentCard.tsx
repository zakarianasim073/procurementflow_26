import { FileText, Download } from 'lucide-react'
import { cn } from '@shared/lib/cn'

export interface DocumentCardProps {
  name: string
  type: string
  size?: string
  section?: string
  onDownload?: () => void
  className?: string
}

export function DocumentCard({ name, type, size, section, onDownload, className }: DocumentCardProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-3 transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-900',
        className,
      )}
    >
      <FileText size={16} className="shrink-0 text-gray-400 dark:text-gray-500" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{name}</p>
        <div className="flex gap-2 text-[10px] text-gray-400 dark:text-gray-500">
          <span>{type}</span>
          {size && <span>{size}</span>}
          {section && <span>{section}</span>}
        </div>
      </div>
      {onDownload && (
        <button
          type="button"
          onClick={onDownload}
          className="shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
          aria-label={`Download ${name}`}
        >
          <Download size={14} />
        </button>
      )}
    </div>
  )
}
