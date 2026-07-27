import { useFeedbackStats, useFeedbackAwaiting } from '@hooks/feedback'
import { FeedbackStats, FeedbackReminder } from '@widgets/feedback'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'

export function FeedbackStatsPage() {
  const { data: stats, isLoading: statsLoading } = useFeedbackStats()
  const { data: awaiting, isLoading: awaitingLoading } = useFeedbackAwaiting()

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Feedback & Learning</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">Track your bidding outcomes and help us improve ProcureFlow</p>
        </div>
      }
      primary={
        <div className="space-y-6">
          {/* Awaiting Feedback */}
          {!awaitingLoading && awaiting && awaiting.length > 0 && (
            <FeedbackReminder />
          )}

          {/* Statistics */}
          <div className="space-y-4">
            <div className="border-b border-gray-200 pb-4 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Your Metrics (30 Days)</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">Based on submitted feedback and bid outcomes</p>
            </div>

            {statsLoading ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-32 rounded-xl" />
                ))}
              </div>
            ) : stats ? (
              <FeedbackStats />
            ) : (
              <EmptyState
                title="No feedback data yet"
                description="Submit feedback on closed tenders to see your metrics"
                icon="BarChart3"
              />
            )}
          </div>

          {/* Trend Charts (placeholder for future implementation) */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Bid Rate Trend</h3>
              <div className="flex items-center justify-center h-40 rounded-lg bg-gray-50 dark:bg-gray-900/30">
                <p className="text-sm text-gray-500 dark:text-gray-400">Chart coming soon</p>
              </div>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Win Rate Trend</h3>
              <div className="flex items-center justify-center h-40 rounded-lg bg-gray-50 dark:bg-gray-900/30">
                <p className="text-sm text-gray-500 dark:text-gray-400">Chart coming soon</p>
              </div>
            </div>
          </div>
        </div>
      }
    >
      {/* Hidden content that would appear if needed */}
    </ScreenTemplate>
  )
}