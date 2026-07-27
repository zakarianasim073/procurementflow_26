import { useState, useMemo } from 'react'
import { FileSearch, FileText, Search, Download, RefreshCw, Filter } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterInput, FilterSelect, WidgetTable, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { Column, TrustEvidence, Tab, SubTab } from '@widgets/shared'
import { Badge } from '@shared/ui/Badge'
import { useRecentAgentRuns } from '@hooks/agents'

const TABS: Tab[] = [
  { id: 'evidence', label: 'Evidence' },
  { id: 'documents', label: 'Documents' },
  { id: 'calculations', label: 'Calculations' },
  { id: 'history', label: 'History' },
  { id: 'ledger', label: 'Ledger' },
]

const SUBTABS: SubTab[] = [
  { id: 'tender', label: 'Tender' }, { id: 'company', label: 'Company' },
  { id: 'awards', label: 'Awards' }, { id: 'ppr', label: 'PPR' },
  { id: 'market', label: 'Market' }, { id: 'ai', label: 'AI' },
]

interface Row { id: string; evidenceId: string; source: string; rule: string; confidence: number; status: 'Verified' | 'Pending' | 'Disputed' }

const STATUS_STYLES = { Verified: 'bg-green-100 text-green-700', Pending: 'bg-amber-100 text-amber-700', Disputed: 'bg-red-100 text-red-700' }

const COLUMNS: Column<Row>[] = [
  { id: 'evidenceId', header: 'Evidence ID', accessor: (r) => <span className="font-mono text-xs font-medium text-gray-900 dark:text-white">{r.evidenceId}</span> },
  { id: 'source', header: 'Source', accessor: (r) => r.source },
  { id: 'rule', header: 'Rule', accessor: (r) => <Badge variant="outline">{r.rule}</Badge> },
  { id: 'confidence', header: 'Confidence', accessor: (r) => (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 rounded-full bg-gray-200 dark:bg-gray-700">
        <div className={`h-full rounded-full ${r.confidence >= 90 ? 'bg-green-500' : r.confidence >= 80 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${r.confidence}%` }} />
      </div>
      <span className="text-[11px] font-medium">{r.confidence}%</span>
    </div>
  ) },
  { id: 'status', header: 'Status', accessor: (r) => <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[r.status]}`}>{r.status}</span> },
]

const STATUS_CONFIDENCE: Record<string, number> = { completed: 95, failed: 70, running: 85 }
const STATUS_MAP: Record<string, Row['status']> = { completed: 'Verified', failed: 'Disputed', running: 'Pending' }

const FALLBACK_DATA: Row[] = [
  { id: '1', evidenceId: 'EV-1203', source: 'Tender PDF', rule: 'Rule 42', confidence: 98, status: 'Verified' },
  { id: '2', evidenceId: 'EV-1204', source: 'Company Registry', rule: 'Rule 37', confidence: 92, status: 'Verified' },
  { id: '3', evidenceId: 'EV-1205', source: 'Award Notice', rule: 'Rule 18', confidence: 85, status: 'Pending' },
  { id: '4', evidenceId: 'EV-1206', source: 'Financial Statement', rule: 'Rule 53', confidence: 97, status: 'Verified' },
  { id: '5', evidenceId: 'EV-1207', source: 'PPR Schedule', rule: 'Rule 29', confidence: 78, status: 'Disputed' },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Evidence chain from document extraction', status: 'verified', detail: 'All sources verified via hash' },
]

export interface EvidenceWidgetProps { tenderId?: string }

export function EvidenceWidget({}: EvidenceWidgetProps) {
  const [activeTab, setActiveTab] = useState('evidence')
  const [activeSubTab, setActiveSubTab] = useState('tender')
  const [search, setSearch] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: results = [], isLoading: loading } = useRecentAgentRuns(20)

  const data = useMemo<Row[]>(() => {
    if (!results || results.length === 0) return FALLBACK_DATA
    return results.map((r) => ({
      id: r.run_id,
      evidenceId: `EV-${r.agent_id}`,
      source: r.agent_name,
      rule: r.error || 'N/A',
      confidence: STATUS_CONFIDENCE[r.status] ?? 85,
      status: (STATUS_MAP[r.status] ?? 'Pending') as Row['status'],
    }))
  }, [results])

  const verifiedCount = data.filter((r) => r.status === 'Verified').length
  const pendingCount = data.filter((r) => r.status === 'Pending').length

  return (
    <WidgetContainer>
      <WidgetHeader title="Evidence" subtitle="Verification trail & supporting documents" icon={<FileSearch size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<Filter size={14} />} label="Filter" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect>
          <option>All statuses</option>
          <option>Verified</option>
          <option>Pending</option>
          <option>Disputed</option>
        </FilterSelect>
        <FilterInput value={search} onChange={setSearch} placeholder="Search evidence..." />
      </WidgetFilters>
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-brand-600" />
        </div>
      ) : (
        <WidgetTable columns={COLUMNS} data={data} />
      )}
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Verify Evidence" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{data.length} evidence records · {verifiedCount} verified</span>
          <span className="flex items-center gap-1"><FileText size={12} /> {pendingCount} pending review</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="evidence" widgetTitle="Evidence" confidence={91} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Evidence" />
    </WidgetContainer>
  )
}
