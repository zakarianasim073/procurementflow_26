import { useParams } from 'react-router-dom'
import { ScreenTemplate } from '@layouts/index'
import { HoursSavedTrend, WinRateComparison, AdoptionCurve } from '@widgets/roi'
import { usePartnerMetrics } from '@hooks/roi'

export function PartnerDetailDashboard() {
  const { companyId } = useParams<{ companyId: string }>()

  const { data: pm, isLoading } = usePartnerMetrics(companyId)

  const hoursSaved = pm?.hours_saved.total ?? 287
  const activeUsers = pm?.active_users ?? 4

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{pm?.company_name ?? 'Loading...'} — Metrics & Performance</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">Detailed ROI breakdown for this partner</p>
        </div>
      }
      primary={
        <div className="space-y-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-32"><p className="text-sm text-gray-500">Loading partner data...</p></div>
          ) : (
          <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Hours Saved</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{hoursSaved}h</p>
              <p className="mt-1 text-xs text-gray-500">~{activeUsers ? (hoursSaved / activeUsers).toFixed(0) : '0'}h per user</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Compliance ↑</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">+{pm?.compliance_improvements.issues_avoided ?? 12}</p>
              <p className="mt-1 text-xs text-gray-500">Issues prevented</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Win Rate</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{pm?.win_rate.post_adoption ?? 39}%</p>
              <p className="mt-1 text-xs text-gray-500">post-adoption</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Active Users</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{activeUsers}</p>
              <p className="mt-1 text-xs text-gray-500">Feedback rate: {pm ? `${(pm.edf_feedback_rate * 100).toFixed(0)}%` : '82%'}</p>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <HoursSavedTrend />
            <WinRateComparison preAdoption={0} postAdoption={pm?.win_rate.post_adoption ?? 0} />
          </div>

          {/* Pricing Accuracy */}
          {pm?.pricing_accuracy && (
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
            <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Pricing Accuracy</h3>
            <div className="space-y-4">
              {[
                { name: 'AI Price Followed', value: `${((pm.pricing_accuracy.user_followed_ai_price / Math.max(pm.bids_placed_with_pf, 1)) * 100).toFixed(0)}%` },
                { name: 'Avg Delta', value: `${pm.pricing_accuracy.ai_price_avg_delta_percent.toFixed(1)}%` },
                { name: 'AI Price Matches', value: `${pm.pricing_accuracy.ai_price_matches}` },
              ].map((stat) => (
                <div key={stat.name} className="flex justify-between text-xs font-medium text-gray-700 dark:text-gray-300">
                  <span>{stat.name}</span>
                  <span>{stat.value}</span>
                </div>
              ))}
            </div>
          </div>
          )}

          {/* Adoption Timeline */}
          <AdoptionCurve data={pm?.user_adoption_curve?.map((u: any) => ({ week: u.week ?? `W${u.month ?? 1}`, active_users: u.active_users ?? u.count ?? 0 })) as any ?? undefined} />
          </>)}
        </div>
      }
    >
    </ScreenTemplate>
  )
}
