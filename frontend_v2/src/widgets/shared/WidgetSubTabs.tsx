import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

export interface SubTab {
  id: string
  label: string
  icon?: ReactNode
}

interface WidgetSubTabsProps {
  subtabs: SubTab[]
  activeSubTab: string
  onSubTabChange: (subtabId: string) => void
  className?: string
}

export function WidgetSubTabs({ subtabs, activeSubTab, onSubTabChange, className }: WidgetSubTabsProps) {
  return (
    <div className={cn('flex gap-0.5 border-b border-gray-50 bg-gray-50/50 px-4 py-1.5 dark:border-gray-800 dark:bg-gray-800/30', className)}>
      {subtabs.map((st) => (
        <button
          key={st.id}
          type="button"
          onClick={() => onSubTabChange(st.id)}
          className={cn(
            'flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors',
            activeSubTab === st.id
              ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300',
          )}
        >
          {st.icon && <span>{st.icon}</span>}
          {st.label}
        </button>
      ))}
    </div>
  )
}
