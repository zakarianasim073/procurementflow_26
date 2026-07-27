import { useExecutiveReport, useLiveMetrics, usePredictionsModelStatus } from '@hooks/index'
import { RecommendationCard, RecommendationCardSkeleton } from './RecommendationCard'

export function AiSummary() {
  const report = useExecutiveReport()
  const metrics = useLiveMetrics()
  const modelStatus = usePredictionsModelStatus()

  const isLoading = report.isLoading || metrics.isLoading || modelStatus.isLoading
  const error = report.error

  if (isLoading) {
    return <RecommendationCardSkeleton />
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
        Couldn't load AI summary.{' '}
        <button onClick={() => report.refetch()} className="underline font-medium">Retry.</button>
      </div>
    )
  }

  const r = report.data?.report
  if (!r) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No AI recommendation ready yet. Run a tender analysis first.
        </p>
      </div>
    )
  }

  const modelInfo = modelStatus.data
  const marketData = metrics.data

  return (
    <div className="space-y-3">
      <RecommendationCard
        decision={r.bid_suggestion.decision}
        probability={r.win_prediction.probability}
        confidence={r.win_prediction.confidence}
        strategy={r.bid_suggestion.strategy}
        actionItems={r.procurement_head_decision.action_items}
      />

      {(modelInfo || marketData) && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <div className="space-y-2 text-xs text-gray-500 dark:text-gray-400">
            {marketData?.overview && (
              <div className="flex justify-between">
                <span>Market Tenders</span>
                <span className="tabular-nums text-gray-700 dark:text-gray-300">{marketData.overview.total_tenders.toLocaleString()}</span>
              </div>
            )}
            {marketData?.overview && (
              <div className="flex justify-between">
                <span>Market Value</span>
                <span className="tabular-nums text-gray-700 dark:text-gray-300">{(marketData.overview.total_value_bdt / 1e7).toFixed(1)}Cr</span>
              </div>
            )}
            {modelInfo?.tender_price_model?.training_samples != null && (
              <div className="flex justify-between">
                <span>ML Training Samples</span>
                <span className="tabular-nums text-gray-700 dark:text-gray-300">{modelInfo.tender_price_model.training_samples.toLocaleString()}</span>
              </div>
            )}
            {modelInfo?.tender_price_model?.trained_at && (
              <div className="flex justify-between">
                <span>Model Last Trained</span>
                <span className="tabular-nums text-gray-700 dark:text-gray-300">
                  {new Date(modelInfo.tender_price_model.trained_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
