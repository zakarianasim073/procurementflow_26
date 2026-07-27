import type { FC } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface HistoricalComparisonProps {
  discount: number
}

export const HistoricalComparison: FC<HistoricalComparisonProps> = ({ discount }) => {
  const data = [
    { discount: 0, avgMargin: 18, count: 2 },
    { discount: -2, avgMargin: 17.8, count: 5 },
    { discount: -5, avgMargin: 17.2, count: 8 },
    { discount: -8, avgMargin: 16.5, count: 12 },
    { discount: -10, avgMargin: 15.8, count: 9 },
    { discount: -12, avgMargin: 15.1, count: 15 },
    { discount: -15, avgMargin: 14.2, count: 11 },
    { discount: -18, avgMargin: 13.1, count: 7 },
    { discount: -20, avgMargin: 12.5, count: 4 },
    { discount: -25, avgMargin: 10.8, count: 3 },
    { discount: -30, avgMargin: 9.2, count: 1 },
  ]

  const currentData = data.find((d) => d.discount === discount)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Historical Comparison</h3>

      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
          <defs>
            <linearGradient id="colorMargin" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-orange-500)" stopOpacity={0.8} />
              <stop offset="95%" stopColor="var(--color-orange-500)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-gray-200)" />
          <XAxis
            dataKey="discount"
            stroke="var(--color-gray-600)"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="var(--color-gray-600)"
            style={{ fontSize: '12px' }}
          />
          <Tooltip
            formatter={(value: any) => `${value}%`}
            labelFormatter={(label) => `Discount: ${label}%`}
            contentStyle={{ backgroundColor: 'var(--color-gray-900)', border: 'none', borderRadius: '8px' }}
            labelStyle={{ color: 'var(--color-gray-100)' }}
          />
          <Area
            type="monotone"
            dataKey="avgMargin"
            stroke="var(--color-orange-600)"
            fillOpacity={1}
            fill="url(#colorMargin)"
            name="Avg Margin %"
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-orange-50 p-3 dark:bg-orange-900/30">
        <div>
          <p className="text-xs font-medium text-orange-600 dark:text-orange-400">Your Position</p>
          <p className="text-lg font-bold text-orange-900 dark:text-orange-300">{discount}%</p>
        </div>
        {currentData && (
          <>
            <div>
              <p className="text-xs font-medium text-orange-600 dark:text-orange-400">Historical Avg Margin</p>
              <p className="text-lg font-bold text-orange-900 dark:text-orange-300">{currentData.avgMargin}%</p>
            </div>
            <div className="col-span-2">
              <p className="text-xs font-medium text-orange-600 dark:text-orange-400">Comparable Bids</p>
              <p className="text-sm text-orange-700 dark:text-orange-400">{currentData.count} past bids at {discount}% discount</p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
