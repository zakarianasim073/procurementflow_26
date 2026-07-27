import { type Column, WidgetTable } from '@widgets/shared'

interface RuleRow { id: string; rule: string; status: 'PASS' | 'WARNING' | 'FAIL'; confidence: number; risk: 'Low' | 'Medium' | 'High' }

const STATUS_STYLES = { PASS: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400', WARNING: 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400', FAIL: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400' }
const RISK_STYLES = { Low: 'text-green-600', Medium: 'text-amber-600', High: 'text-red-600' }

const COLUMNS: Column<RuleRow>[] = [
  { id: 'rule', header: 'Rule', accessor: (r) => <span className="font-medium text-gray-900 dark:text-white">{r.rule}</span> },
  { id: 'status', header: 'Status', accessor: (r) => <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[r.status]}`}>{r.status}</span> },
  { id: 'confidence', header: 'Confidence', accessor: (r) => <span className="font-medium">{r.confidence}%</span>, align: 'center' },
  { id: 'risk', header: 'Risk', accessor: (r) => <span className={`font-medium ${RISK_STYLES[r.risk]}`}>{r.risk}</span> },
]

interface RuleTableProps { data?: RuleRow[]; loading?: boolean }

export function RuleTable({ data = [], loading }: RuleTableProps) {
  return <WidgetTable columns={COLUMNS} data={data} loading={loading} emptyMessage="No rules evaluated" />
}
