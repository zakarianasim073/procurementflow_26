import type { FC } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface WinProbabilityCurveProps {
  discount: number
  winProbability: number
}

export const WinProbabilityCurve: FC<WinProbabilityCurveProps> = ({ discount, winProbability }) => {
  const data = Array.from({ length: 31 }, (_, i) => {
    const d = -i
    const prob = Math.max(10, Math.min(95, 50 + Math.abs(d) * 3))
    return { discount: d, probability: prob, actual: d === discount }
  })

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Win Probability Curve</h3>

      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-gray-200)" />
          <XAxis
            dataKey="discount"
            stroke="var(--color-gray-600)"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="var(--color-gray-600)"
            domain={[0, 100]}
            style={{ fontSize: '12px' }}
          />
          <Tooltip
            formatter={(value: any) => `${value}%`}
            labelFormatter={(label) => `Discount: ${label}%`}
            contentStyle={{ backgroundColor: 'var(--color-gray-900)', border: 'none', borderRadius: '8px' }}
            labelStyle={{ color: 'var(--color-gray-100)' }}
          />
          <Line
            type="monotone"
            dataKey="probability"
            stroke="var(--color-green-500)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          {/* Highlight current discount */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="transparent"
            dot={(props: any) => {
              if (props.payload.actual) {
                return (
                  <circle
                    cx={props.cx}
                    cy={props.cy}
                    r={4}
                    fill="var(--color-blue-600)"
                    stroke="var(--color-white)"
                    strokeWidth={2}
                  />
                )
              }
              return null
            }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-4 rounded-lg bg-green-50 p-3 dark:bg-green-900/30">
        <p className="text-xs font-medium text-green-600 dark:text-green-400">Your Current Position</p>
        <div className="mt-1 flex items-baseline gap-2">
          <p className="text-2xl font-bold text-green-900 dark:text-green-300">{winProbability.toFixed(0)}%</p>
          <p className="text-xs text-green-700 dark:text-green-400">at {discount}% discount</p>
        </div>
      </div>
    </div>
  )
}
