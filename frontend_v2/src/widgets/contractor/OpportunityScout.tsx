interface Opportunity {
  tender_id: string
  tender_name: string
  agency: string
  category: string
  value: number
  match_score: number
  reason: string
  partner_recommendation?: string
}

interface OpportunityScoutProps {
  opportunities?: Opportunity[]
  onSelectOpportunity?: (tenderId: string) => void
}

export function OpportunityScout({
  opportunities = [],
  onSelectOpportunity,
}: OpportunityScoutProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Recommended Opportunities</h3>
      {opportunities.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No opportunities found</div>
      ) : (
        <div className="space-y-3">
          {opportunities.map((opp) => {
            const matchColor =
              opp.match_score >= 90
                ? 'border-green-200 bg-green-50 dark:border-green-700 dark:bg-green-900/30'
                : opp.match_score >= 70
                  ? 'border-yellow-200 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-900/30'
                  : 'border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-900/30'

            return (
              <div
                key={opp.tender_id}
                onClick={() => onSelectOpportunity?.(opp.tender_id)}
                className={`cursor-pointer rounded-lg border p-4 transition-all hover:shadow-md ${matchColor}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-sm text-gray-900 dark:text-white">{opp.tender_name}</p>
                    <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{opp.agency} • {opp.category}</p>
                    <p className="mt-2 text-xs text-gray-700 dark:text-gray-300">{opp.reason}</p>
                    {opp.partner_recommendation && (
                      <p className="mt-2 text-xs font-medium text-blue-600 dark:text-blue-400">
                        💡 Consider partnering with {opp.partner_recommendation}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-gray-900 dark:text-white">{opp.match_score}%</div>
                    <p className="text-xs text-gray-600 dark:text-gray-400">match</p>
                    <p className="mt-2 text-sm font-semibold text-gray-900 dark:text-white tabular-nums">
                      {(opp.value / 1e7).toFixed(1)}Cr
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
