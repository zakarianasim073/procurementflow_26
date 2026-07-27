import type { ReactNode } from 'react'
import clsx from 'clsx'
import { cn } from '@shared/lib/cn'
import { TrustPanel } from './TrustPanel'
import { ConfidenceMeter } from './ConfidenceMeter'

export interface RecommendationCardProps {
  decision: 'Bidding Recommended' | 'Marginal Value (Proceed with Caution)' | 'Do Not Bid'
  confidence: number
  strategy?: string
  evidence?: ReactNode
  actionItems?: string[]
  className?: string
}

const decisionConfig = {
  'Bidding Recommended': { tone: 'passed' as const, badge: 'bg-success-50 text-success-700 dark:bg-success-950 dark:text-success-300' },
  'Marginal Value (Proceed with Caution)': { tone: 'warning' as const, badge: 'bg-warning-50 text-warning-700 dark:bg-warning-950 dark:text-warning-300' },
  'Do Not Bid': { tone: 'unavailable' as const, badge: 'bg-danger-50 text-danger-700 dark:bg-danger-950 dark:text-danger-300' },
}

export function RecommendationCard({ decision, confidence, strategy, evidence, actionItems, className }: RecommendationCardProps) {
  const config = decisionConfig[decision]

  return (
    <div className={cn('space-y-3', className)}>
      <TrustPanel verdict={config.tone} confidence={confidence}>
        <div className="space-y-3">
          <span className={clsx('inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold', config.badge)}>
            {decision}
          </span>

          <ConfidenceMeter value={confidence} label="Win Probability" />

          {strategy && (
            <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-400">{strategy}</p>
          )}

          {evidence}

          {actionItems && actionItems.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Next actions</p>
              <ul className="space-y-1">
                {actionItems.slice(0, 3).map((item, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                    <span className="mt-0.5 h-1 w-1 shrink-0 rounded-full bg-gray-400" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </TrustPanel>
    </div>
  )
}
