import { Users, AlertCircle, CheckCircle, Shield } from 'lucide-react'

interface ClauseHeaderProps {
  clause: {
    id?: string
    code?: string
    category?: string
    priority?: 'high' | 'medium' | 'low'
  }
  isSelected?: boolean
  onClick?: () => void
}

export function ClauseHeader({ clause, isSelected, onClick }: ClauseHeaderProps) {
  const priorityConfig = {
    high: { icon: AlertCircle, color: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800' },
    medium: { icon: Shield, color: 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800' },
    low: { icon: CheckCircle, color: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800' },
  }

  const config = priorityConfig[clause.priority || 'medium']
  const Icon = config.icon

  return (
    <div
      className={`group relative rounded-lg border ${config.border} bg-white p-3 transition-all hover:shadow-md dark:bg-gray-800 cursor-pointer ${isSelected ? 'ring-2 ring-blue-500' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {clause.code && (
            <div className="font-mono text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              {clause.code}
            </div>
          )}
          <div className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2">
            {clause.code ? clause.code.replace(/-/g, ' ').split(' ').slice(-2).join(' ').replace('-', ' ') : 'Clause'}
          </div>
          {clause.category && (
            <div className="flex items-center gap-1 mt-1 text-xs text-gray-500 dark:text-gray-400">
              <Users className="h-3 w-3" />
              <span>{clause.category}</span>
            </div>
          )}
        </div>
        <div className={`p-2 rounded-lg ${config.color}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      {isSelected && (
        <div className="absolute inset-0 rounded-lg ring-2 ring-blue-500 pointer-events-none" />
      )}
    </div>
  )
}
