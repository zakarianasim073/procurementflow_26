import type { FC } from 'react'

interface Scenario {
  label: string
  discount: number
  type: 'conservative' | 'competitive' | 'aggressive'
  description?: string
}

interface ScenarioButtonsProps {
  scenarios: Scenario[]
  selectedDiscount: number
  onScenarioSelect: (discount: number) => void
  onSaveStrategy?: () => void
  onShareStrategy?: () => void
}

export const ScenarioButtons: FC<ScenarioButtonsProps> = ({
  scenarios,
  selectedDiscount,
  onScenarioSelect,
  onSaveStrategy,
  onShareStrategy,
}) => {
  const getScenarioStyles = (type: string, isActive: boolean) => {
    const baseClass = 'w-full rounded-lg p-3 text-left transition-all border'
    if (isActive) {
      switch (type) {
        case 'conservative':
          return `${baseClass} border-2 border-blue-500 bg-blue-50 dark:bg-blue-900/30`
        case 'competitive':
          return `${baseClass} border-2 border-orange-500 bg-orange-50 dark:bg-orange-900/30`
        case 'aggressive':
          return `${baseClass} border-2 border-red-500 bg-red-50 dark:bg-red-900/30`
      }
    }
    return `${baseClass} border-gray-200 bg-gray-50 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-900/50 dark:hover:bg-gray-900`
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Pre-built Scenarios</h3>

      <div className="space-y-2">
        {scenarios.map((scenario) => {
          const isActive = selectedDiscount === scenario.discount
          return (
            <button
              key={scenario.discount}
              onClick={() => onScenarioSelect(scenario.discount)}
              className={getScenarioStyles(scenario.type, isActive)}
              aria-pressed={isActive}
            >
              <p className="text-sm font-semibold text-gray-900 dark:text-white">{scenario.label}</p>
              <p className="text-xs text-gray-600 dark:text-gray-400">{scenario.discount}% discount</p>
              {scenario.description && (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{scenario.description}</p>
              )}
            </button>
          )
        })}
      </div>

      <div className="mt-4 space-y-2">
        <button
          onClick={onSaveStrategy}
          className="w-full rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          aria-label="Save pricing strategy"
        >
          Save Strategy
        </button>
        <button
          onClick={onShareStrategy}
          className="w-full rounded-lg border border-gray-200 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-900 transition-colors"
          aria-label="Share strategy URL"
        >
          Share Strategy
        </button>
      </div>
    </div>
  )
}
