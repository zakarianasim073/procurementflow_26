import { useState } from 'react'
import { BookOpen, ArrowRight, Clock, User } from 'lucide-react'

interface RelatedClausesPanelProps {
  relatedClauses: {
    id: string
    code: string
    title: string
    relevance_score: number
    category: string
    summary: string
    last_updated: string
  }[]
  maxVisible?: number
}

export function RelatedClausesPanel({ relatedClauses, maxVisible = 5 }: RelatedClausesPanelProps) {
  const [showAll, setShowAll] = useState(false)
  
  const displayClauses = showAll ? relatedClauses : relatedClauses.slice(0, maxVisible)
  
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Related Clauses</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Referenced in this context (based on semantic similarity)
            </p>
          </div>
          <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {relatedClauses.length} clause{relatedClauses.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>
      
      <div className="p-4 space-y-3">
        {displayClauses.map((clause) => (
          <div
            key={clause.id}
            className="group cursor-pointer rounded-lg border border-gray-200 bg-white p-3 transition-all hover:bg-blue-50 hover:border-blue-200 dark:border-gray-700 dark:bg-gray-800/60 dark:hover:bg-blue-900/20 dark:hover:border-blue-700"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <BookOpen className="h-3 w-3 text-gray-600 dark:text-gray-400" />
                  <span className="font-mono text-sm font-semibold text-gray-900 dark:text-white">
                    {clause.code}
                  </span>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                    {clause.relevance_score}% match
                  </span>
                </div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2">
                  {clause.title}
                </h4>
              </div>
              <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-blue-500" />
            </div>
            
            <div className="space-y-2">
              <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                {clause.summary}
              </p>
              
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                <div className="flex items-center gap-1">
                  <User className="h-3 w-3" />
                  <span>{clause.category}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span>{clause.last_updated}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {relatedClauses.length === 0 && (
          <div className="text-center py-8">
            <BookOpen className="mx-auto h-8 w-8 text-gray-400" />
            <p className="text-gray-500 dark:text-gray-400 mt-2">No related clauses found</p>
          </div>
        )}
      </div>
      
      {relatedClauses.length > maxVisible && (
        <div className="border-t border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
          <button
            onClick={() => setShowAll(!showAll)}
            className="w-full text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            {showAll ? 'Show less' : `Show all ${relatedClauses.length} clauses`}
          </button>
        </div>
      )}
    </div>
  )
}
