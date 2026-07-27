import { FileText, ExternalLink, Scale, Shield, CheckCircle } from 'lucide-react'

interface PrecedentCardProps {
  precedent: {
    id: string
    case_reference: string
    court: string
    date: string
    excerpt: string
    outcome: string
    relevance_score: number
    clause_refs: string[]
  }
}

export function PrecedentCard({ precedent }: PrecedentCardProps) {
  const getRelevanceColor = (score: number) => {
    if (score >= 90) return 'text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900/30'
    if (score >= 75) return 'text-blue-700 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30'
    if (score >= 60) return 'text-yellow-700 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30'
    return 'text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900/30'
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm transition-all hover:shadow-md dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-gray-600 dark:text-gray-400" />
              <span className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
                {precedent.case_reference}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {precedent.court}, {precedent.date}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Scale className="h-3 w-3 text-gray-600 dark:text-gray-400" />
              <Shield className="h-3 w-3 text-gray-600 dark:text-gray-400" />
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Relevant to {precedent.clause_refs.join(', ')}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className={`rounded-full px-3 py-1 text-sm font-bold ${getRelevanceColor(precedent.relevance_score)}`}>
              {precedent.relevance_score}% Relevant
            </div>
          </div>
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Key Excerpt</h4>
          <p className="text-sm text-gray-700 dark:text-gray-300 italic">
            "{precedent.excerpt}"
          </p>
        </div>
        
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Outcome</h4>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {precedent.outcome}
          </p>
        </div>
      </div>
      
      <div className="border-t border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <CheckCircle className="h-3 w-3" />
            <span>Verified precedent</span>
          </div>
          <button
            className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
            onClick={() => window.open('#', '_blank')}
          >
            <ExternalLink className="h-3 w-3" />
            View full case
          </button>
        </div>
      </div>
    </div>
  )
}
