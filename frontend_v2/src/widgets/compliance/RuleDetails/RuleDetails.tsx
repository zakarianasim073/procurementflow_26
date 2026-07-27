import { CheckCircle, AlertTriangle, XCircle, FileText } from 'lucide-react'

interface RuleDetailsProps {
  rule: { id: string; name: string; status: string; description: string; evidence: string[] }
  onClose?: () => void
}

const STATUS_ICON_MAP = { PASS: CheckCircle, WARNING: AlertTriangle, FAIL: XCircle } as const
const STATUS_COLOR_MAP = { PASS: 'text-green-500', WARNING: 'text-amber-500', FAIL: 'text-red-500' } as const

export function RuleDetails({ rule, onClose }: RuleDetailsProps) {
  const StatusIcon = STATUS_ICON_MAP[rule.status as keyof typeof STATUS_ICON_MAP] ?? CheckCircle
  const statusColor = STATUS_COLOR_MAP[rule.status as keyof typeof STATUS_COLOR_MAP] ?? 'text-gray-500'

  return (
    <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusIcon size={16} className={statusColor} />
          <span className="text-sm font-semibold text-gray-900 dark:text-white">{rule.name}</span>
        </div>
        {onClose && (<button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600">&times;</button>)}
      </div>
      <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">{rule.description}</p>
      <div>
        <p className="text-[11px] font-medium text-gray-500 mb-1.5">Supporting Evidence</p>
        {rule.evidence.map((ev, i) => (
          <div key={i} className="flex items-center gap-1.5 mb-1">
            <FileText size={11} className="text-gray-400" />
            <span className="text-xs text-gray-700 dark:text-gray-300">{ev}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
