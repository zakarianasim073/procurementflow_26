import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'

export interface Tab {
  id: string
  label: string
  count?: number
  icon?: ReactNode
}

interface WidgetTabsProps {
  tabs: Tab[]
  activeTab: string
  onTabChange: (tabId: string) => void
  className?: string
}

export function WidgetTabs({ tabs, activeTab, onTabChange, className }: WidgetTabsProps) {
  return (
    <div className={cn('flex gap-1 border-b border-gray-100 px-4 dark:border-gray-800', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onTabChange(tab.id)}
          className={cn(
            'relative flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium transition-colors',
            'hover:text-gray-900 dark:hover:text-white',
            activeTab === tab.id
              ? 'text-brand-600 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-brand-500 dark:text-brand-400'
              : 'text-gray-500 dark:text-gray-400',
          )}
        >
          {tab.icon && <span>{tab.icon}</span>}
          {tab.label}
          {tab.count !== undefined && (
            <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
