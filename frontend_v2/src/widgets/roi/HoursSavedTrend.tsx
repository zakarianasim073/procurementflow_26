import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface HoursSavedTrendProps {
  data?: Array<{ week: string; hours: number }>
}

export function HoursSavedTrend({ data = [] }: HoursSavedTrendProps) {
  const chartData = data.length > 0 ? data : generateMockData()

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Hours Saved Over Time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="colorHours" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-gray-700" />
          <XAxis dataKey="week" stroke="#6b7280" className="dark:stroke-gray-500" />
          <YAxis stroke="#6b7280" className="dark:stroke-gray-500" />
          <Tooltip
            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb' }}
          />
          <Area type="monotone" dataKey="hours" stroke="#3b82f6" fillOpacity={1} fill="url(#colorHours)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function generateMockData() {
  return [
    { week: 'Week 1', hours: 45 },
    { week: 'Week 2', hours: 92 },
    { week: 'Week 3', hours: 156 },
    { week: 'Week 4', hours: 234 },
  ]
}
