import { AlertCircle, Info, Lightbulb, FileText } from 'lucide-react'

interface CommonMistakesPanelProps {
  mistakes: {
    id: string
    type: 'technical' | 'procedural' | 'interpretation' | 'documentation'
    severity: 'critical' | 'moderate' | 'minor'
    description: string
    impact: string
    solution: string
    clause_refs: string[]
  }[]
}

export function CommonMistakesPanel({ mistakes }: CommonMistakesPanelProps) {
  const getTypeConfig = (type: string) => {
    const configs = {
      technical: { icon: AlertCircle, color: 'blue', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800' },
      procedural: { icon: FileText, color: 'green', bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800' },
      interpretation: { icon: Lightbulb, color: 'purple', bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-200 dark:border-purple-800' },
      documentation: { icon: Info, color: 'orange', bg: 'bg-orange-50 dark:bg-orange-900/20', border: 'border-orange-200 dark:border-orange-800' },
    }
    return configs[type as keyof typeof configs] || configs.procedural
  }

  const getSeverityConfig = (severity: string) => {
    const configs = {
      critical: { label: 'Critical', color: 'text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900/30' },
      moderate: { label: 'Moderate', color: 'text-yellow-700 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30' },
      minor: { label: 'Minor', color: 'text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900/30' },
    }
    return configs[severity as keyof typeof configs] || configs.minor
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Common Mistakes</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Discover frequent errors and how to avoid them
        </p>
      </div>
      
      <div className="p-4 space-y-4">
        {mistakes.map((mistake) => {
          const typeConfig = getTypeConfig(mistake.type)
          const severityConfig = getSeverityConfig(mistake.severity)
          const Icon = typeConfig.icon

          return (
            <div key={mistake.id} className="group rounded-lg border border-gray-200 bg-white p-4 transition-all hover:shadow-md dark:border-gray-700 dark:bg-gray-800/60">
              <div className="flex items-start gap-3">
                <div className={`rounded-lg ${typeConfig.bg} ${typeConfig.border} border p-2`}>
                  <Icon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{mistake.description}</h4>
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${severityConfig.color}`}>
                      {severityConfig.label}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <p className="text-gray-700 dark:text-gray-300">
                      <span className="font-medium">Impact:</span> {mistake.impact}
                    </p>
                    <p className="text-gray-700 dark:text-gray-300">
                      <span className="font-medium">Solution:</span> {mistake.solution}
                    </p>
                    <p className="text-gray-600 dark:text-gray-400 text-xs">
                      <span className="font-medium">Related clauses:</span> {mistake.clause_refs.join(', ')}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
        
        {mistakes.length === 0 && (
          <div className="text-center py-8">
            <Info className="mx-auto h-8 w-8 text-gray-400" />
            <p className="text-gray-500 dark:text-gray-400 mt-2">No common mistakes documented for this clause</p>
          </div>
        )}
      </div>
    </div>
  )
}