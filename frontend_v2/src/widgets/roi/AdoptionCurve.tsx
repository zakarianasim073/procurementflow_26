import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface AdoptionCurveProps {
  data?: Array<{ week: string; active_users: number }>
}

export function AdoptionCurve({ data = [] }: AdoptionCurveProps) {
  const chartData = data.length > 0 ? data : generateMockData()

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">User Adoption Curve</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-gray-700" />
          <XAxis dataKey="week" stroke="#6b7280" className="dark:stroke-gray-500" />
          <YAxis stroke="#6b7280" className="dark:stroke-gray-500" />
          <Tooltip
            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb' }}
          />
          <Line
            type="monotone"
            dataKey="active_users"
            stroke="#06b6d4"
            dot={{ fill: '#06b6d4', r: 4 }}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-4 text-xs text-gray-600 dark:text-gray-400">
        Trend: <span className="font-semibold text-green-600 dark:text-green-400">Accelerating</span>
      </p>
    </div>
  )
}

function generateMockData() {
  return [
    { week: 'Week 1', active_users: 2 },
    { week: 'Week 2', active_users: 5 },
    { week: 'Week 3', active_users: 8 },
    { week: 'Week 4', active_users: 12 },
    { week: 'Week 5', active_users: 15 },
  ]
}
