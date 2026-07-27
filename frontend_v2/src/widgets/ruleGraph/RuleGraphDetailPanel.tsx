import { X, Link, FileText, TrendingDown } from 'lucide-react'

interface Relationship {
  type: 'requires' | 'contradicts' | 'overrides' | 'clarifies'
  targetRuleId: string
  targetRuleLabel: string
}

interface RuleGraphDetailPanelProps {
  ruleId?: string
  ruleLabel?: string
  description?: string
  incomingRelationships?: Relationship[]
  outgoingRelationships?: Relationship[]
  onClose?: () => void
}

export function RuleGraphDetailPanel({
  ruleId = 'R42',
  ruleLabel = 'General Evaluation Principles',
  description = 'Ensures that evaluation is conducted fairly and based on objective criteria.',
  incomingRelationships = [
    { type: 'requires', targetRuleId: 'R38', targetRuleLabel: 'Financial Capacity' },
    { type: 'requires', targetRuleId: 'R40', targetRuleLabel: 'Technical Capacity' },
  ],
  outgoingRelationships = [
    { type: 'requires', targetRuleId: 'R43', targetRuleLabel: 'Financial Evaluation' },
    { type: 'clarifies', targetRuleId: 'R63', targetRuleLabel: 'Guidance Document' },
  ],
  onClose,
}: RuleGraphDetailPanelProps) {
  const relationshipIcons = {
    requires: <Link className="h-4 w-4 text-green-600 dark:text-green-400" />,
    contradicts: <TrendingDown className="h-4 w-4 text-red-600 dark:text-red-400" />,
    overrides: <FileText className="h-4 w-4 text-orange-600 dark:text-orange-400" />,
    clarifies: <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />,
  }

  const relationshipLabels = {
    requires: 'Requires',
    contradicts: 'Contradicts',
    overrides: 'Overrides',
    clarifies: 'Clarifies',
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden max-w-sm">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 p-4 flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">{ruleId}</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">{ruleLabel}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-900 rounded transition-colors"
        >
          <X className="h-4 w-4 text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Description */}
        <div>
          <p className="text-sm text-gray-700 dark:text-gray-300">{description}</p>
        </div>

        {/* Incoming Relationships */}
        {incomingRelationships.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-900 dark:text-white mb-2">Incoming</h4>
            <div className="space-y-2">
              {incomingRelationships.map((rel) => (
                <div key={`${rel.targetRuleId}-in`} className="flex items-start gap-2 p-2 rounded bg-gray-50 dark:bg-gray-900/50">
                  {relationshipIcons[rel.type]}
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-900 dark:text-white">{rel.targetRuleId}</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">{relationshipLabels[rel.type]}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Outgoing Relationships */}
        {outgoingRelationships.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-900 dark:text-white mb-2">Outgoing</h4>
            <div className="space-y-2">
              {outgoingRelationships.map((rel) => (
                <div key={`${rel.targetRuleId}-out`} className="flex items-start gap-2 p-2 rounded bg-gray-50 dark:bg-gray-900/50">
                  {relationshipIcons[rel.type]}
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-900 dark:text-white">{rel.targetRuleId}</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">{relationshipLabels[rel.type]}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA */}
        <button className="w-full py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors">
          View Full Clause
        </button>
      </div>
    </div>
  )
}
