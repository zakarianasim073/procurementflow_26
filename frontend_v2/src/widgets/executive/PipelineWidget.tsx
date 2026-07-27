import { useState } from 'react'
import { Layers, Filter, Eye, Download, RefreshCw, Search, Settings } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterSelect, FilterInput, WidgetTable, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { Column, TrustEvidence, Tab, SubTab } from '@widgets/shared'
import { Badge } from '@shared/ui/Badge'

const PIPELINE_TABS: Tab[] = [
  { id: 'all', label: 'All', count: 8 },
  { id: 'submitted', label: 'Submitted', count: 3 },
  { id: 'evaluated', label: 'Evaluated', count: 2 },
  { id: 'awarded', label: 'Awarded', count: 2 },
  { id: 'lost', label: 'Lost', count: 1 },
]

const PIPELINE_SUBTABS: SubTab[] = [
  { id: 'this-week', label: 'This Week' },
  { id: 'this-month', label: 'This Month' },
  { id: 'quarter', label: 'Quarter' },
  { id: 'agency', label: 'Agency' },
  { id: 'category', label: 'Category' },
  { id: 'value', label: 'Value' },
]

interface PipelineRow {
  id: string; tender: string; agency: string; value: string; stage: string; winProb: string; deadline: string
  status: 'on-track' | 'at-risk' | 'overdue'
}

const PIPELINE_DATA: PipelineRow[] = [
  { id: '1', tender: 'BWDB-24/2026', agency: 'BWDB', value: '৳2.1 Cr', stage: 'Evaluation', winProb: '86%', deadline: '4 days', status: 'on-track' },
  { id: '2', tender: 'LGED-18/2026', agency: 'LGED', value: '৳1.3 Cr', stage: 'Submission', winProb: '73%', deadline: '2 days', status: 'at-risk' },
  { id: '3', tender: 'PWD-07/2026', agency: 'PWD', value: '৳4.5 Cr', stage: 'Preparation', winProb: '91%', deadline: '12 days', status: 'on-track' },
  { id: '4', tender: 'RHD-03/2026', agency: 'RHD', value: '৳0.8 Cr', stage: 'Awarded', winProb: '100%', deadline: 'Completed', status: 'on-track' },
]

const STATUS_STYLES = { 'on-track': 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400', 'at-risk': 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400', 'overdue': 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400' }

const COLUMNS: Column<PipelineRow>[] = [
  { id: 'tender', header: 'Tender', accessor: (r) => <span className="font-medium text-gray-900 dark:text-white">{r.tender}</span> },
  { id: 'agency', header: 'Agency', accessor: (r) => <Badge variant="outline">{r.agency}</Badge> },
  { id: 'value', header: 'Value', accessor: (r) => r.value, align: 'right' },
  { id: 'stage', header: 'Stage', accessor: (r) => r.stage },
  { id: 'winProb', header: 'Win %', accessor: (r) => r.winProb, align: 'center' },
  { id: 'deadline', header: 'Deadline', accessor: (r) => r.deadline, align: 'center' },
  { id: 'status', header: 'Status', accessor: (r) => <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[r.status]}`}>{r.status.replace('-', ' ')}</span> },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Pipeline data from tender DB', status: 'verified', detail: 'Live sync from procurement_tenders' },
  { id: 'ev-2', label: 'Win probability from AI model', status: 'verified', detail: 'v2.4 Bayesian model' },
]

export function PipelineWidget() {
  const [activeTab, setActiveTab] = useState('all')
  const [activeSubTab, setActiveSubTab] = useState('this-week')
  const [filterValue, setFilterValue] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <WidgetContainer>
      <WidgetHeader title="Pipeline" subtitle="Active tender pipeline" icon={<Layers size={16} />} actions={
        <ToolbarButton icon={<Settings size={14} />} label="" />
      } />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<Filter size={14} />} label="Filter" />
        <ToolbarButton icon={<Eye size={14} />} label="Columns" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
      </WidgetToolbar>
      <WidgetTabs tabs={PIPELINE_TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={PIPELINE_SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect value={activeSubTab} onChange={(e) => setActiveSubTab(e.target.value)}>
          <option value="this-week">This Week</option>
          <option value="this-month">This Month</option>
          <option value="quarter">Quarter</option>
        </FilterSelect>
        <FilterInput value={filterValue} onChange={setFilterValue} placeholder="Search tenders..." />
      </WidgetFilters>
      <WidgetTable columns={COLUMNS} data={PIPELINE_DATA} />
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Analyze Pipeline" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{PIPELINE_DATA.length} active tenders</span>
          <span>Total value: ৳8.7 Cr</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="pipeline" widgetTitle="Pipeline" confidence={88} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Pipeline" />
    </WidgetContainer>
  )
}
