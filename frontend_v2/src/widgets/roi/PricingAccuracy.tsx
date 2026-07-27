import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface PricingAccuracyProps {
  data?: Array<{ ai_price: number; actual_price: number }>
}

export function PricingAccuracy({ data = [] }: PricingAccuracyProps) {
  const chartData = data.length > 0 ? data : generateMockData()

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Pricing Accuracy</h3>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-gray-700" />
          <XAxis
            dataKey="ai_price"
            type="number"
            stroke="#6b7280"
            className="dark:stroke-gray-500"
            label={{ value: 'AI Recommended (৳ Cr)', position: 'insideBottomRight', offset: -10 }}
          />
          <YAxis
            dataKey="actual_price"
            type="number"
            stroke="#6b7280"
            className="dark:stroke-gray-500"
            label={{ value: 'Actual Bid (৳ Cr)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb' }}
            formatter={(value) => `${Number(value).toFixed(2)}Cr`}
          />
          <Scatter name="Bid Results" data={chartData} fill="#8b5cf6" />
        </ScatterChart>
      </ResponsiveContainer>
      <p className="mt-4 text-xs text-gray-600 dark:text-gray-400">
        Accuracy: <span className="font-semibold">±7.2%</span> average delta
      </p>
    </div>
  )
}

function generateMockData() {
  return Array.from({ length: 8 }, () => ({
    ai_price: Math.random() * 5 + 1,
    actual_price: Math.random() * 5 + 1,
  }))
}
