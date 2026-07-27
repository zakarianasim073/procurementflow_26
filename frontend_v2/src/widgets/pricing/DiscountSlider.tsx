import type { FC } from 'react'

interface DiscountSliderProps {
  value: number
  onChange: (value: number) => void
  sorBaseline: number
  cost: number
}

export const DiscountSlider: FC<DiscountSliderProps> = ({ value, onChange, sorBaseline, cost }) => {
  const bidPrice = sorBaseline * (1 + value / 100)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Discount Strategy</h3>

      <div className="space-y-4">
        <div>
          <label className="mb-2 block text-xs font-medium text-gray-600 dark:text-gray-400">
            Discount from SOR
          </label>
          <input
            type="range"
            min="-30"
            max="0"
            step="1"
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            className="w-full accent-blue-500"
            aria-label="Pricing discount slider"
          />
          <div className="mt-2 flex justify-between text-xs text-gray-600 dark:text-gray-400">
            <span>0%</span>
            <span className="font-semibold text-blue-600 dark:text-blue-400">{value}%</span>
            <span>–30%</span>
          </div>
        </div>

        <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/30">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400">SOR Baseline</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white">৳{(sorBaseline / 1e7).toFixed(1)}Cr</p>
        </div>

        <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-900/30">
          <p className="text-xs font-medium text-blue-600 dark:text-blue-400">Your Bid Price</p>
          <p className="text-lg font-bold text-blue-900 dark:text-blue-300">৳{(bidPrice / 1e7).toFixed(2)}Cr</p>
        </div>

        <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/30">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Your Cost</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white">৳{(cost / 1e7).toFixed(1)}Cr</p>
        </div>
      </div>
    </div>
  )
}
