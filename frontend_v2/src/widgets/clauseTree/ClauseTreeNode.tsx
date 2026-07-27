import { ChevronDown } from 'lucide-react'

export interface ClauseTreeNodeProps {
  id: string
  label: string
  level?: 'schedule' | 'section' | 'rule' | 'subsection'
  children?: ClauseTreeNodeProps[]
  mistakeCount?: number
  isActive?: boolean
  isExpanded?: boolean
  onToggle?: (id: string) => void
  onSelect?: (id: string) => void
}

export function ClauseTreeNode({
  id,
  label,
  level: _level,
  children = [],
  mistakeCount,
  isActive,
  isExpanded,
  onToggle,
  onSelect,
}: ClauseTreeNodeProps) {
  const hasChildren = children.length > 0

  const getMistakeColor = (count?: number) => {
    if (!count) return 'text-gray-600 dark:text-gray-400'
    if (count <= 3) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/30'
    if (count <= 6) return 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30'
    return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30'
  }

  return (
    <div className="select-none">
      <div
        className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
          isActive
            ? 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-300'
            : 'hover:bg-gray-100 dark:hover:bg-gray-900/40 text-gray-700 dark:text-gray-300'
        }`}
        onClick={() => onSelect?.(id)}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggle?.(id)
            }}
            className="p-0 hover:bg-gray-200 dark:hover:bg-gray-800 rounded"
          >
            <ChevronDown
              className={`h-4 w-4 transition-transform ${isExpanded ? '' : '-rotate-90'}`}
            />
          </button>
        )}
        {!hasChildren && <div className="w-4" />}

        <span className="flex-1 text-sm font-medium">{label}</span>

        {mistakeCount && mistakeCount > 0 && (
          <span className={`px-2 py-1 rounded text-xs font-semibold ${getMistakeColor(mistakeCount)}`}>
            {mistakeCount} ⚠️
          </span>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div className="ml-4 border-l border-gray-200 dark:border-gray-700">
          {children.map((child) => (
            <ClauseTreeNode
              key={child.id}
              {...child}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}
