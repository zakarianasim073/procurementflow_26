import type { FC } from 'react'

interface ExpectedValueCardProps {
  expectedValue: number
  marginIfWon: number
  winProbability: number
}

export const ExpectedValueCard: FC<ExpectedValueCardProps> = ({
  expectedValue,
  marginIfWon,
  winProbability,
}) => {
  const recommendation =
    expectedValue > 50e6 ? 'Strong bid' : expectedValue > 20e6 ? 'Acceptable bid' : 'Risky bid'

  return (
    <div className="rounded-lg border-2 border-purple-200 bg-purple-50 p-4 dark:border-purple-700 dark:bg-purple-900/30">
      <p className="text-xs font-medium text-purple-600 dark:text-purple-400">Expected Value</p>
      <p className="mt-1 text-2xl font-bold text-purple-900 dark:text-purple-300">
        ৳{(expectedValue / 1e7).toFixed(2)}Cr
      </p>

      <p className="mt-1 text-xs text-purple-700 dark:text-purple-400">
        E[profit] = margin × win probability
      </p>

      <div className="mt-3 space-y-2 border-t border-purple-200 pt-3 dark:border-purple-700">
        <div className="flex justify-between text-xs">
          <span className="text-purple-700 dark:text-purple-400">Margin if won:</span>
          <span className="font-semibold text-purple-900 dark:text-purple-300">
            ৳{(marginIfWon / 1e7).toFixed(2)}Cr
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-purple-700 dark:text-purple-400">Win probability:</span>
          <span className="font-semibold text-purple-900 dark:text-purple-300">{winProbability.toFixed(0)}%</span>
        </div>
      </div>

      <div className="mt-3 rounded bg-purple-100 p-2 dark:bg-purple-900/50">
        <p className="text-xs font-medium text-purple-800 dark:text-purple-200">{recommendation}</p>
        <p className="mt-1 text-xs text-purple-700 dark:text-purple-300">
          {expectedValue > 50e6
            ? 'Strong expected value. This bid balances competitiveness and profitability.'
            : expectedValue > 20e6
              ? 'Acceptable expected value, but monitor risk carefully.'
              : 'Low expected value. Consider revising your strategy.'}
        </p>
      </div>
    </div>
  )
}
