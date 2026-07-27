import { type Column, WidgetTable } from '@widgets/shared'
import { Badge } from '@shared/ui/Badge'

interface EvidenceRow { id: string; evidenceId: string; source: string; rule: string; confidence: number; status: 'Verified' | 'Pending' | 'Disputed' }

const STATUS_STYLES = { Verified: 'bg-green-100 text-green-700', Pending: 'bg-amber-100 text-amber-700', Disputed: 'bg-red-100 text-red-700' }

const COLUMNS: Column<EvidenceRow>[] = [
  { id: 'evidenceId', header: 'Evidence ID', accessor: (r) => <span className="font-mono text-xs">{r.evidenceId}</span> },
  { id: 'source', header: 'Source', accessor: (r) => r.source },
  { id: 'rule', header: 'Rule', accessor: (r) => <Badge variant="outline">{r.rule}</Badge> },
  { id: 'confidence', header: 'Confidence', accessor: (r) => <span className="font-medium">{r.confidence}%</span>, align: 'center' },
  { id: 'status', header: 'Status', accessor: (r) => <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[r.status]}`}>{r.status}</span> },
]

interface EvidenceTableProps { data?: EvidenceRow[]; loading?: boolean }

export function EvidenceTable({ data = [], loading }: EvidenceTableProps) {
  return <WidgetTable columns={COLUMNS} data={data} loading={loading} emptyMessage="No evidence records" />
}
