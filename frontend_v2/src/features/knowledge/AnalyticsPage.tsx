import { BarChart3, TrendingUp, Users, FileText } from 'lucide-react'
import { Card } from '@shared/ui/Card'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { ScreenTemplate } from '@layouts/index'
import { useLiveMetrics } from '@hooks/index'

export function AnalyticsPage() {
  const metrics = useLiveMetrics()

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Analytics</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Market analytics and performance insights</p>
        </div>
      }
      primary={
        <div className="space-y-6">
          {metrics.isLoading ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
            </div>
          ) : metrics.data?.overview ? (
            <>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <Card className="p-4">
                  <div className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-blue-500" />
                    <span className="text-xs text-gray-500 dark:text-gray-400">Total Tenders</span>
                  </div>
                  <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.data.overview.total_tenders.toLocaleString()}
                  </p>
                </Card>
                <Card className="p-4">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-green-500" />
                    <span className="text-xs text-gray-500 dark:text-gray-400">Awarded</span>
                  </div>
                  <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.data.overview.awarded_count?.toLocaleString() ?? '—'}
                  </p>
                </Card>
                <Card className="p-4">
                  <div className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-purple-500" />
                    <span className="text-xs text-gray-500 dark:text-gray-400">Top Contractors</span>
                  </div>
                  <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.data.top_contractors?.length ?? 0}
                  </p>
                </Card>
                <Card className="p-4">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-orange-500" />
                    <span className="text-xs text-gray-500 dark:text-gray-400">Top Agencies</span>
                  </div>
                  <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.data.top_agencies?.length ?? 0}
                  </p>
                </Card>
              </div>

              {/* Top Agencies */}
              {metrics.data.top_agencies && metrics.data.top_agencies.length > 0 && (
                <Card className="p-4">
                  <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Top Agencies</h2>
                  <div className="space-y-2">
                    {metrics.data.top_agencies.slice(0, 10).map((agency, i) => (
                      <div key={agency.agency_code ?? i} className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                        <div className="flex items-center gap-3">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                            {i + 1}
                          </span>
                          <span className="text-sm text-gray-900 dark:text-white">
                            {agency.agency_name || agency.agency_code || 'Unknown'}
                          </span>
                        </div>
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                          {agency.tender_count.toLocaleString()} tenders
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Top Contractors */}
              {metrics.data.top_contractors && metrics.data.top_contractors.length > 0 && (
                <Card className="p-4">
                  <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Top Contractors</h2>
                  <div className="space-y-2">
                    {metrics.data.top_contractors.slice(0, 10).map((contractor, i) => (
                      <div key={contractor.contractor_name ?? i} className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                        <div className="flex items-center gap-3">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-100 text-xs font-medium text-green-700 dark:bg-green-900 dark:text-green-300">
                            {i + 1}
                          </span>
                          <span className="text-sm text-gray-900 dark:text-white">{contractor.contractor_name || 'Unknown'}</span>
                        </div>
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                          {contractor.award_count.toLocaleString()} awards · ৳{(contractor.avg_award_value_bdt / 1e7).toFixed(1)}Cr avg
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </>
          ) : (
            <EmptyState
              title="No analytics data"
              description="Analytics data will appear when tenders are tracked in the system."
            />
          )}
        </div>
      }
    />
  )
}
