import { Filter, Settings } from 'lucide-react'

interface RuleGraphControlPanelProps {
  relationshipTypes?: Array<'requires' | 'contradicts' | 'overrides' | 'clarifies'>
  onFilterChange?: (types: string[]) => void
  layout?: 'cluster' | 'hierarchy' | 'force'
  onLayoutChange?: (layout: 'cluster' | 'hierarchy' | 'force') => void
}

export function RuleGraphControlPanel({
  relationshipTypes = ['requires', 'contradicts', 'overrides', 'clarifies'],
  onFilterChange,
  layout = 'cluster',
  onLayoutChange,
}: RuleGraphControlPanelProps) {
  const allTypes = ['requires', 'contradicts', 'overrides', 'clarifies'] as const

  const typeColors = {
    requires: 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-700',
    contradicts: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-700',
    overrides: 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-700',
    clarifies: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-700',
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 space-y-4">
      {/* Layout Control */}
      <div>
        <label className="flex items-center gap-2 mb-2 text-xs font-semibold text-gray-900 dark:text-white">
          <Settings className="h-4 w-4" />
          Layout Mode
        </label>
        <div className="flex gap-2">
          {(['cluster', 'hierarchy', 'force'] as const).map((l) => (
            <button
              key={l}
              onClick={() => onLayoutChange?.(l)}
              className={`flex-1 px-3 py-2 text-xs font-medium rounded border transition-colors ${
                layout === l
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900'
              }`}
            >
              {l === 'cluster' ? 'Cluster' : l === 'hierarchy' ? 'Hierarchy' : 'Force'}
            </button>
          ))}
        </div>
      </div>

      {/* Relationship Filters */}
      <div>
        <label className="flex items-center gap-2 mb-2 text-xs font-semibold text-gray-900 dark:text-white">
          <Filter className="h-4 w-4" />
          Relationships
        </label>
        <div className="space-y-2">
          {allTypes.map((type) => {
            const isSelected = relationshipTypes.includes(type)
            return (
              <label key={type} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={(_e) => {
                    const newTypes = isSelected
                      ? relationshipTypes.filter((t) => t !== type)
                      : [...relationshipTypes, type]
                    onFilterChange?.(newTypes)
                  }}
                  className="rounded"
                />
                <span className={`inline-block px-2 py-1 rounded text-xs font-medium border ${typeColors[type]}`}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </span>
              </label>
            )
          })}
        </div>
      </div>

      {/* Info */}
      <div className="rounded-lg bg-gray-50 dark:bg-gray-900/50 p-3">
        <p className="text-xs text-gray-600 dark:text-gray-400">
          💡 Hover over nodes to see relationships. Click to view details.
        </p>
      </div>
    </div>
  )
}
