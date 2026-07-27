import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface WinRateComparisonProps {
  preAdoption?: number
  postAdoption?: number
}

export function WinRateComparison({ preAdoption = 24, postAdoption = 38 }: WinRateComparisonProps) {
  const data = [
    { name: 'Pre-Adoption', rate: preAdoption },
    { name: 'Post-Adoption', rate: postAdoption },
  ]

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Win Rate: Before & After</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-gray-700" />
          <XAxis dataKey="name" stroke="#6b7280" className="dark:stroke-gray-500" />
          <YAxis stroke="#6b7280" className="dark:stroke-gray-500" />
          <Tooltip
            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb' }}
            formatter={(value) => `${value}%`}
          />
          <Bar dataKey="rate" fill="#10b981" />
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-4 text-xs text-gray-600 dark:text-gray-400">
        Improvement: <span className="font-semibold text-green-600 dark:text-green-400">+{((postAdoption - preAdoption) / preAdoption * 100).toFixed(1)}%</span>
      </p>
    </div>
  )
}
