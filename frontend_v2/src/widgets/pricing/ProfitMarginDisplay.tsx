import type { FC } from 'react'

interface ProfitMarginDisplayProps {
  marginPercent: number
  marginIfWon: number
  bidPrice: number
  cost: number
}

export const ProfitMarginDisplay: FC<ProfitMarginDisplayProps> = ({
  marginPercent,
  marginIfWon,
  bidPrice,
  cost,
}) => {
  const riskLevel = marginPercent < 5 ? 'critical' : marginPercent < 10 ? 'warning' : 'healthy'

  return (
    <div
      className={`rounded-lg border-2 p-4 ${
        riskLevel === 'critical'
          ? 'border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-900/30'
          : riskLevel === 'warning'
            ? 'border-orange-200 bg-orange-50 dark:border-orange-700 dark:bg-orange-900/30'
            : 'border-green-200 bg-green-50 dark:border-green-700 dark:bg-green-900/30'
      }`}
    >
      <p
        className={`text-xs font-medium ${
          riskLevel === 'critical'
            ? 'text-red-600 dark:text-red-400'
            : riskLevel === 'warning'
              ? 'text-orange-600 dark:text-orange-400'
              : 'text-green-600 dark:text-green-400'
        }`}
      >
        Profit Margin
      </p>
      <p
        className={`mt-1 text-2xl font-bold ${
          riskLevel === 'critical'
            ? 'text-red-900 dark:text-red-300'
            : riskLevel === 'warning'
              ? 'text-orange-900 dark:text-orange-300'
              : 'text-green-900 dark:text-green-300'
        }`}
      >
        {marginPercent.toFixed(1)}%
      </p>

      <div className="mt-3 space-y-2 text-xs">
        <div className="flex justify-between">
          <span
            className={
              riskLevel === 'critical'
                ? 'text-red-700 dark:text-red-400'
                : riskLevel === 'warning'
                  ? 'text-orange-700 dark:text-orange-400'
                  : 'text-green-700 dark:text-green-400'
            }
          >
            If you win:
          </span>
          <span className="font-semibold">৳{(marginIfWon / 1e7).toFixed(2)}Cr</span>
        </div>
        <div className="flex justify-between">
          <span
            className={
              riskLevel === 'critical'
                ? 'text-red-700 dark:text-red-400'
                : riskLevel === 'warning'
                  ? 'text-orange-700 dark:text-orange-400'
                  : 'text-green-700 dark:text-green-400'
            }
          >
            Bid price:
          </span>
          <span className="font-semibold">৳{(bidPrice / 1e7).toFixed(2)}Cr</span>
        </div>
        <div className="flex justify-between">
          <span
            className={
              riskLevel === 'critical'
                ? 'text-red-700 dark:text-red-400'
                : riskLevel === 'warning'
                  ? 'text-orange-700 dark:text-orange-400'
                  : 'text-green-700 dark:text-green-400'
            }
          >
            Cost:
          </span>
          <span className="font-semibold">৳{(cost / 1e7).toFixed(1)}Cr</span>
        </div>
      </div>

      {riskLevel === 'critical' && (
        <p className="mt-3 rounded bg-red-100 p-2 text-xs text-red-800 dark:bg-red-900/50 dark:text-red-200">
          ⚠️ Very thin margin. Consider increasing bid price or reducing cost.
        </p>
      )}
    </div>
  )
}
