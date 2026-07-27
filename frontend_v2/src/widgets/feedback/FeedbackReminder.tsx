import { Bell, Clock, CheckCircle } from 'lucide-react'
import { useFeedbackStats } from '@hooks/feedback'

export function FeedbackReminder() {
  const { data: stats, isLoading } = useFeedbackStats()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700"></div>
          <div className="h-3 w-48 rounded bg-gray-200 dark:bg-gray-700"></div>
        </div>
      </div>
    )
  }

  if (!stats) {
    return null
  }

  const totalAwaiting = stats.total_tenders_recommended - stats.bids_placed

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-200 p-4 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-yellow-600" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Feedback Reminders</h3>
        </div>
      </div>
      
      <div className="p-4">
        {totalAwaiting <= 0 ? (
          <div className="text-center py-6">
            <CheckCircle className="mx-auto mb-2 h-8 w-8 text-green-500" />
            <p className="text-sm text-gray-600 dark:text-gray-400">No awaiting feedback</p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-blue-500" />
                <span className="text-sm font-medium text-gray-900 dark:text-white">Total Awaiting</span>
              </div>
              <span className="text-lg font-bold text-blue-600 dark:text-blue-400">
                {totalAwaiting}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
