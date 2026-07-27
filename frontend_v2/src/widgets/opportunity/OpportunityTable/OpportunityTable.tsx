import { type Column, WidgetTable } from '@widgets/shared'
import { Badge } from '@shared/ui/Badge'

interface OpportunityRow {
  id: string; tender: string; agency: string; aiScore: number; winPct: string
  profit: string; closing: string; action: 'Open' | 'Analyze' | 'Submit'
}

const COLUMNS: Column<OpportunityRow>[] = [
  { id: 'tender', header: 'Tender', accessor: (r) => <span className="font-medium text-gray-900 dark:text-white">{r.tender}</span> },
  { id: 'agency', header: 'Agency', accessor: (r) => <Badge variant="outline">{r.agency}</Badge> },
  { id: 'aiScore', header: 'AI Score', accessor: (r) => (<span className={`font-semibold ${r.aiScore >= 90 ? 'text-green-600' : r.aiScore >= 75 ? 'text-amber-600' : 'text-gray-600'}`}>{r.aiScore}%</span>), align: 'center' },
  { id: 'winPct', header: 'Win %', accessor: (r) => <span className="font-medium">{r.winPct}</span>, align: 'center' },
  { id: 'profit', header: 'Profit', accessor: (r) => <span className="font-semibold text-gray-900 dark:text-white">{r.profit}</span>, align: 'right' },
  { id: 'closing', header: 'Closing', accessor: (r) => { const d = parseInt(r.closing); return <span className={`text-xs font-medium ${d <= 3 ? 'text-red-600' : d <= 7 ? 'text-amber-600' : 'text-gray-600'}`}>{r.closing}</span> }, align: 'center' },
  { id: 'action', header: 'Action', accessor: (r) => (<button type="button" className="rounded-md bg-brand-500 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-brand-600">{r.action}</button>), align: 'center' },
]

interface OpportunityTableProps {
  data?: OpportunityRow[]
  loading?: boolean
}

export function OpportunityTable({ data = [], loading }: OpportunityTableProps) {
  return <WidgetTable columns={COLUMNS} data={data} loading={loading} emptyMessage="No opportunities found" />
}
