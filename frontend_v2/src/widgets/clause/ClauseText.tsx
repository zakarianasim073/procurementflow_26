import { Copy, FileText, AlertTriangle, Download, Eye } from 'lucide-react'

interface ClauseTextProps {
  clause: {
    id: string
    code: string
    title: string
    text: string
    category: string
    examples: string[]
    attachments: { name: string; url: string; type: string }[]
  }
  onCopy?: (text: string) => void
  onViewAttachment?: (url: string, type: string) => void
}

export function ClauseText({ clause, onCopy, onViewAttachment }: ClauseTextProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-mono text-lg font-semibold text-gray-900 dark:text-white">{clause.code}</h3>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mt-1">{clause.title}</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onCopy?.(clause.text)}
              className="rounded-lg bg-gray-100 p-2 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600"
              title="Copy clause text"
            >
              <Copy className="h-4 w-4" />
            </button>
            {clause.attachments.length > 0 && (
              <div className="relative group">
                <button
                  onClick={() => onViewAttachment?.(clause.attachments[0].url, clause.attachments[0].type)}
                  className="rounded-lg bg-gray-100 p-2 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600"
                  title="View attachments"
                >
                  <FileText className="h-4 w-4" />
                </button>
                <div className="absolute right-0 top-full mt-1 hidden rounded-lg border border-gray-200 bg-white p-1 shadow-lg group-hover:block dark:border-gray-700 dark:bg-gray-800">
                  {clause.attachments.map((attachment, index) => (
                    <button
                      key={index}
                      onClick={() => onViewAttachment?.(attachment.url, attachment.type)}
                      className="block w-full rounded-lg px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                    >
                      <div className="flex items-center gap-2">
                        <Download className="h-3 w-3" />
                        <span>{attachment.name}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="mt-2 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <AlertTriangle className="h-4 w-4" />
            {clause.category}
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-4 w-4" />
            {clause.attachments.length} attachment{clause.attachments.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>
      
      <div className="p-6">
        <div className="prose max-w-none dark:prose-invert">
          <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
            {clause.text}
          </p>
        </div>
        
        {clause.examples.length > 0 && (
          <div className="mt-6">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Examples</h4>
            <div className="space-y-2">
              {clause.examples.map((example, index) => (
                <div key={index} className="flex gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/60">
                  <span className="flex-shrink-0 rounded-full bg-gray-200 px-2 py-1 text-xs font-medium text-gray-600 dark:bg-gray-600 dark:text-gray-300">
                    {index + 1}
                  </span>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{example}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      
      <div className="border-t border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <Eye className="h-4 w-4" />
            <span>Last updated: Today</span>
          </div>
          <div className="flex items-center gap-2">
            {clause.attachments.map((attachment, index) => (
              <div key={index} className="flex items-center gap-1 text-xs">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <span className="text-gray-600 dark:text-gray-400">{attachment.type.toUpperCase()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}