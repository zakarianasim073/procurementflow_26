import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface WinRateTrendProps {
  data?: Array<{ year: string; rate: number }>
}

export function WinRateTrend({ data = [] }: WinRateTrendProps) {
  const chartData = data.length > 0 ? data : generateMockData()

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Win Rate Trend</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-gray-700" />
          <XAxis dataKey="year" stroke="#6b7280" className="dark:stroke-gray-500" />
          <YAxis stroke="#6b7280" className="dark:stroke-gray-500" label={{ value: '%', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb' }}
            formatter={(value) => `${value}%`}
          />
          <Line type="monotone" dataKey="rate" stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4', r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-4 text-xs text-gray-600 dark:text-gray-400">
        Trend: <span className="font-semibold text-green-600 dark:text-green-400">Improving (+8% YoY)</span>
      </p>
    </div>
  )
}

function generateMockData() {
  return [
    { year: '2022', rate: 24 },
    { year: '2023', rate: 31 },
    { year: '2024', rate: 38 },
  ]
}
