interface EligibilityStatus {
  rule: string
  status: 'met' | 'gap' | 'exceed'
  detail: string
}

interface EligibilityTrackerProps {
  rule37?: EligibilityStatus
  rule38?: EligibilityStatus
  rule40?: EligibilityStatus
  gaps?: string[]
}

export function EligibilityTracker({
  rule37,
  rule38,
  rule40,
  gaps = [],
}: EligibilityTrackerProps) {
  const defaultRule37 = { rule: 'Rule 37 — Experience', status: 'exceed' as const, detail: '20+ years (target: 15)' }
  const defaultRule38 = { rule: 'Rule 38 — Financial', status: 'met' as const, detail: 'Debt ratio 0.32 (healthy)' }
  const defaultRule40 = { rule: 'Rule 40 — Technical', status: 'met' as const, detail: '85 employees, modern equipment' }

  const rules = [rule37 || defaultRule37, rule38 || defaultRule38, rule40 || defaultRule40]

  const statusIcons = {
    met: '✓',
    gap: '⚠️',
    exceed: '✓✓',
  }

  const statusColors = {
    met: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    gap: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    exceed: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">PPR2025 Eligibility</h3>
      <div className="space-y-3">
        {rules.map((rule) => (
          <div key={rule.rule} className={`rounded-lg p-3 ${statusColors[rule.status]}`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-sm">{rule.rule}</p>
                <p className="text-xs mt-1">{rule.detail}</p>
              </div>
              <span className="text-xl">{statusIcons[rule.status]}</span>
            </div>
          </div>
        ))}
      </div>
      {gaps.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs font-semibold text-red-600 dark:text-red-400 mb-2">Qualification Gaps:</p>
          <ul className="space-y-1">
            {gaps.map((gap, idx) => (
              <li key={idx} className="text-xs text-gray-600 dark:text-gray-400">
                • {gap}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
