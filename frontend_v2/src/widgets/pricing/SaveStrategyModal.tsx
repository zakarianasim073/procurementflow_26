import type { FC } from 'react'
import { useState } from 'react'

interface SaveStrategyModalProps {
  isOpen: boolean
  onClose: () => void
  onSave?: (strategy: PricingStrategy) => void
  discount: number
  expectedValue: number
  winProbability: number
}

export interface PricingStrategy {
  name: string
  rationale: string
  discount: number
  expectedValue: number
  winProbability: number
  tags: string[]
}

export const SaveStrategyModal: FC<SaveStrategyModalProps> = ({
  isOpen,
  onClose,
  onSave,
  discount,
  expectedValue,
  winProbability,
}) => {
  const [name, setName] = useState(`Strategy ${discount}%`)
  const [rationale, setRationale] = useState('')
  const [tags, setTags] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  if (!isOpen) return null

  const handleSave = async () => {
    setIsSaving(true)
    try {
      onSave?.({
        name,
        rationale,
        discount,
        expectedValue,
        winProbability,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter((t) => t),
      })
      setName(`Strategy ${discount}%`)
      setRationale('')
      setTags('')
      onClose()
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70">
      <div className="w-full max-w-2xl rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Save Pricing Strategy</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        <div className="mb-4 rounded-lg bg-gray-50 p-4 dark:bg-gray-900/30">
          <div className="grid grid-cols-3 gap-4 text-center text-xs">
            <div>
              <p className="font-medium text-gray-600 dark:text-gray-400">Discount</p>
              <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{discount}%</p>
            </div>
            <div>
              <p className="font-medium text-gray-600 dark:text-gray-400">Win Probability</p>
              <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{winProbability.toFixed(0)}%</p>
            </div>
            <div>
              <p className="font-medium text-gray-600 dark:text-gray-400">Expected Value</p>
              <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">
                ৳{(expectedValue / 1e7).toFixed(2)}Cr
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white">
              Strategy Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              placeholder="e.g., Conservative Bid Q3"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white">
              Rationale
            </label>
            <textarea
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              rows={4}
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              placeholder="Why did you choose this strategy? What are the key assumptions?"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Document your thinking for future reference
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white">
              Tags
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              placeholder="e.g., risky, competitive, margin-focused (comma-separated)"
            />
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={onClose}
            disabled={isSaving}
            className="flex-1 rounded-lg border border-gray-300 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !name.trim()}
            className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save Strategy'}
          </button>
        </div>
      </div>
    </div>
  )
}
