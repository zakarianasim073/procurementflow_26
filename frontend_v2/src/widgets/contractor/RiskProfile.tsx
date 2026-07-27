interface RiskDimension {
  name: string
  level: 'low' | 'medium' | 'high'
  description: string
}

interface RiskProfileProps {
  dimensions?: RiskDimension[]
  overallRisk?: 'low' | 'medium' | 'high'
  flags?: Array<{ severity: 'low' | 'medium' | 'high'; text: string; recommendation: string }>
}

export function RiskProfile({
  dimensions = [],
  overallRisk = 'low',
  flags = [],
}: RiskProfileProps) {
  const defaultDimensions = [
    { name: 'Compliance', level: 'low' as const, description: 'No disqualifications in 2 years' },
    { name: 'Market', level: 'medium' as const, description: 'Zero urban development experience' },
    { name: 'Financial', level: 'low' as const, description: 'Healthy debt ratio (0.32)' },
    { name: 'Operational', level: 'medium' as const, description: 'Safety cert expires next month' },
  ]

  const dims = dimensions.length > 0 ? dimensions : defaultDimensions

  const levelColors = {
    low: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    medium: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    high: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Risk Profile</h3>
        <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${levelColors[overallRisk]}`}>
          Overall: {overallRisk.toUpperCase()}
        </span>
      </div>

      <div className="space-y-3">
        {dims.map((dim) => (
          <div key={dim.name} className={`rounded-lg p-3 ${levelColors[dim.level]}`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-sm">{dim.name}</p>
                <p className="mt-1 text-xs">{dim.description}</p>
              </div>
              <span className="text-lg font-semibold">
                {dim.level === 'low' ? '✓' : dim.level === 'medium' ? '⚠️' : '✕'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {flags.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="mb-2 text-xs font-semibold text-gray-900 dark:text-white">Action Items:</p>
          {flags.map((flag, idx) => (
            <div key={idx} className="mb-2 text-xs text-gray-700 dark:text-gray-300">
              <p>• {flag.text}</p>
              <p className="ml-4 text-gray-600 dark:text-gray-400">→ {flag.recommendation}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
