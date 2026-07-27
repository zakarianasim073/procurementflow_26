

interface Partner {
  company_id: string
  company_name: string
  hours_saved: number
  compliance_improvement: number
  win_rate_improvement: number
  active_users: number
}

interface PartnerRankingsProps {
  partners?: Partner[]
  sortBy?: 'hours' | 'win_rate' | 'compliance'
}

export function PartnerRankings({ partners = [], sortBy = 'hours' }: PartnerRankingsProps) {
  const sorted = [...partners].sort((a, b) => {
    if (sortBy === 'hours') return b.hours_saved - a.hours_saved
    if (sortBy === 'win_rate') return b.win_rate_improvement - a.win_rate_improvement
    return b.compliance_improvement - a.compliance_improvement
  })

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Partner Rankings</h3>
      {sorted.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No partners yet</div>
      ) : (
        <div className="space-y-3">
          {sorted.map((partner, idx) => (
            <div
              key={partner.company_id}
              className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900/50"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-600 dark:bg-blue-900 dark:text-blue-300">
                  {idx + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{partner.company_name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{partner.active_users} active users</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{partner.hours_saved}h</p>
                <p className="text-xs text-green-600 dark:text-green-400">+{partner.win_rate_improvement.toFixed(1)}% win rate</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
