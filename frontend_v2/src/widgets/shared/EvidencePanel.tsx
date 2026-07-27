import { useState } from 'react'
import { cn } from '@shared/lib/cn'
import { Scale, CheckCircle, AlertTriangle, XCircle, ExternalLink } from 'lucide-react'
import { Badge } from '@shared/ui/Badge'

export interface EvidenceItem {
  id: string
  label: string
  source: string
  status: 'verified' | 'warning' | 'failed'
  detail: string
}

interface EvidencePanelProps {
  items: EvidenceItem[]
  className?: string
}

const STATUS_ICONS = { verified: CheckCircle, warning: AlertTriangle, failed: XCircle }
const STATUS_COLORS = { verified: 'text-green-500', warning: 'text-amber-500', failed: 'text-red-500' }

export function EvidencePanel({ items, className }: EvidencePanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  return (
    <div className={cn('rounded-lg border border-gray-100 bg-gray-50/50 dark:border-gray-800 dark:bg-gray-800/20', className)}>
      <div className="flex items-center gap-2 border-b border-gray-100 px-3 py-2 dark:border-gray-800">
        <Scale size={12} className="text-gray-500" />
        <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400">Evidence Trail</span>
        <Badge variant="outline" className="text-[10px] ml-auto">{items.length} items</Badge>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {items.map((item) => {
          const Icon = STATUS_ICONS[item.status]
          const isExpanded = expandedId === item.id
          return (
            <div key={item.id}>
              <button
                type="button"
                onClick={() => setExpandedId(isExpanded ? null : item.id)}
                className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/30"
              >
                <Icon size={12} className={STATUS_COLORS[item.status]} />
                <span className="flex-1 text-xs text-gray-700 dark:text-gray-300">{item.label}</span>
                <span className="text-[10px] text-gray-400">{item.source}</span>
                <ExternalLink size={10} className="text-gray-400" />
              </button>
              {isExpanded && (
                <div className="border-t border-gray-50 bg-white px-3 py-2 dark:border-gray-800 dark:bg-gray-900">
                  <p className="text-[11px] text-gray-500 leading-relaxed">{item.detail}</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
