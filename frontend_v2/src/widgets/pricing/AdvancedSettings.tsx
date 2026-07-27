import type { FC } from 'react'
import { useState } from 'react'

interface AdvancedSettingsModalProps {
  isOpen: boolean
  onClose: () => void
  onSave?: (settings: AdvancedSettings) => void
  competitorCount?: number
  costOverride?: number
  riskTolerance?: 'low' | 'medium' | 'high'
}

export interface AdvancedSettings {
  competitorCount: number
  costOverride: number
  riskTolerance: 'low' | 'medium' | 'high'
  includeHistorical: boolean
}

export const AdvancedSettings: FC<AdvancedSettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
  competitorCount = 5,
  costOverride = 0,
  riskTolerance = 'medium',
}) => {
  const [localSettings, setLocalSettings] = useState<AdvancedSettings>({
    competitorCount,
    costOverride,
    riskTolerance,
    includeHistorical: true,
  })

  if (!isOpen) return null

  const handleSave = () => {
    onSave?.(localSettings)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70">
      <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Advanced Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Close settings"
          >
            ✕
          </button>
        </div>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white">
              Expected Competitor Count
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={localSettings.competitorCount}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, competitorCount: Number(e.target.value) })
              }
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-white"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Used to calculate win probability
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white">
              Cost Override (৳ Cr)
            </label>
            <input
              type="number"
              step="0.1"
              value={localSettings.costOverride}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, costOverride: Number(e.target.value) })
              }
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-white"
              placeholder="0"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Override cost estimate (leave 0 to use default)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white">
              Risk Tolerance
            </label>
            <div className="mt-2 space-y-2">
              {(['low', 'medium', 'high'] as const).map((level) => (
                <label key={level} className="flex items-center">
                  <input
                    type="radio"
                    name="riskTolerance"
                    value={level}
                    checked={localSettings.riskTolerance === level}
                    onChange={(e) =>
                      setLocalSettings({
                        ...localSettings,
                        riskTolerance: e.target.value as 'low' | 'medium' | 'high',
                      })
                    }
                    className="cursor-pointer"
                  />
                  <span className="ml-2 text-sm text-gray-700 dark:text-gray-300 capitalize">
                    {level} Risk
                  </span>
                </label>
              ))}
            </div>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Affects portfolio recommendations
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="historical"
              checked={localSettings.includeHistorical}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, includeHistorical: e.target.checked })
              }
              className="cursor-pointer rounded"
            />
            <label htmlFor="historical" className="text-sm text-gray-700 dark:text-gray-300">
              Include historical bid data
            </label>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-300 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  )
}
