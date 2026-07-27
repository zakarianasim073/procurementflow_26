import type { FC } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

interface CompetitorDistributionProps {
  bidPrice: number
  sorBaseline: number
}

export const CompetitorDistribution: FC<CompetitorDistributionProps> = ({ bidPrice, sorBaseline }) => {
  const yourDiscount = Math.round(((sorBaseline - bidPrice) / sorBaseline) * 100)

  const data = [
    { discount: 0, count: 2, color: 'var(--color-red-500)' },
    { discount: -2, count: 4, color: 'var(--color-orange-500)' },
    { discount: -5, count: 8, color: 'var(--color-yellow-500)' },
    { discount: -8, count: 12, color: 'var(--color-orange-500)' },
    { discount: -10, count: 9, color: 'var(--color-orange-500)' },
    { discount: -12, count: 15, color: 'var(--color-green-500)' },
    { discount: -15, count: 11, color: 'var(--color-blue-500)' },
    { discount: -18, count: 7, color: 'var(--color-blue-500)' },
    { discount: -20, count: 4, color: 'var(--color-purple-500)' },
    { discount: -25, count: 2, color: 'var(--color-purple-500)' },
  ]

  const competitorsBelow = data.filter((d) => d.discount < yourDiscount).reduce((sum, d) => sum + d.count, 0)
  const totalCompetitors = data.reduce((sum, d) => sum + d.count, 0)
  const percentileBeat = Math.round((competitorsBelow / totalCompetitors) * 100)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Competitor Distribution</h3>

      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
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
            formatter={(value: any) => `${value} bidders`}
            labelFormatter={(label) => `Discount: ${label}%`}
            contentStyle={{ backgroundColor: 'var(--color-gray-900)', border: 'none', borderRadius: '8px' }}
            labelStyle={{ color: 'var(--color-gray-100)' }}
          />
          <Bar dataKey="count" name="Bidders" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-blue-50 p-3 dark:bg-blue-900/30">
        <div>
          <p className="text-xs font-medium text-blue-600 dark:text-blue-400">Your Discount</p>
          <p className="text-lg font-bold text-blue-900 dark:text-blue-300">{yourDiscount}%</p>
        </div>
        <div>
          <p className="text-xs font-medium text-blue-600 dark:text-blue-400">Percentile</p>
          <p className="text-lg font-bold text-blue-900 dark:text-blue-300">{percentileBeat}th</p>
        </div>
        <div className="col-span-2">
          <p className="text-xs font-medium text-blue-600 dark:text-blue-400">Competitive Position</p>
          <p className="mt-1 text-sm text-blue-700 dark:text-blue-400">
            You beat {competitorsBelow} out of {totalCompetitors} comparable bidders
          </p>
        </div>
      </div>
    </div>
  )
}
