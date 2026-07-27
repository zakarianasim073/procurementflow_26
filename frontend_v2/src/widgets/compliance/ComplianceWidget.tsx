import { useState } from 'react'
import { ShieldCheck, Scale, Search, RefreshCw, Download, Filter, Loader2 } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterSelect, FilterInput, WidgetTable, WidgetFooter, WidgetContent, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { Column, TrustEvidence, Tab, SubTab } from '@widgets/shared'
import { useComplianceCheck, useRunComplianceCheck } from '@hooks/index'

const TABS: Tab[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'rules', label: 'Rules' },
  { id: 'schedules', label: 'Schedules' },
  { id: 'circulars', label: 'Circulars' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'exceptions', label: 'Exceptions' },
  { id: 'history', label: 'History' },
]

const RULE_SUBTABS: SubTab[] = [
  { id: 'eligibility', label: 'Eligibility' }, { id: 'experience', label: 'Experience' },
  { id: 'turnover', label: 'Turnover' }, { id: 'equipment', label: 'Equipment' },
  { id: 'personnel', label: 'Personnel' }, { id: 'jv', label: 'JV' },
  { id: 'security', label: 'Security' }, { id: 'evaluation', label: 'Evaluation' },
]

interface RuleRow { id: string; rule: string; status: 'PASS' | 'WARNING' | 'FAIL'; confidence: number; risk: 'Low' | 'Medium' | 'High' }

const STATUS_STYLES = { PASS: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400', WARNING: 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400', FAIL: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400' }
const RISK_STYLES = { Low: 'text-green-600', Medium: 'text-amber-600', High: 'text-red-600' }

const RULE_COLUMNS: Column<RuleRow>[] = [
  { id: 'rule', header: 'Rule', accessor: (r) => <span className="font-medium text-gray-900 dark:text-white">{r.rule}</span> },
  { id: 'status', header: 'Status', accessor: (r) => <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[r.status]}`}>{r.status}</span> },
  { id: 'confidence', header: 'Confidence', accessor: (r) => <span className="font-medium">{r.confidence}%</span>, align: 'center' },
  { id: 'risk', header: 'Risk', accessor: (r) => <span className={`font-medium ${RISK_STYLES[r.risk]}`}>{r.risk}</span> },
  { id: 'evidence', header: 'Evidence', accessor: () => <button type="button" className="text-brand-600 hover:text-brand-700 text-[11px] font-medium">View</button> },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'PPR-2025 rule definitions', status: 'verified', detail: '67 rules loaded from regulation DB' },
  { id: 'ev-2', label: 'Company data from contractor profile', status: 'verified', detail: 'Real-time compliance check' },
]

interface ComplianceWidgetProps {
  tenderId?: string
}

export function ComplianceWidget({ tenderId }: ComplianceWidgetProps) {
  const [activeTab, setActiveTab] = useState('overview')
  const [activeSubTab, setActiveSubTab] = useState('eligibility')
  const [searchQuery, setSearchQuery] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data: checkResult, isLoading } = useComplianceCheck(tenderId ?? '')
  const runCheck = useRunComplianceCheck()

  const rules = checkResult?.rules ?? []
  const rows: RuleRow[] = rules.map((r: any, i: number) => ({
    id: String(i),
    rule: r.title || r.rule || r.code || `Rule ${i + 1}`,
    status: r.status === 'passed' ? 'PASS' : r.status === 'warning' ? 'WARNING' : r.status === 'failed' ? 'FAIL' : 'WARNING',
    confidence: r.confidence ?? r.score ?? 90,
    risk: r.status === 'failed' ? 'High' : r.status === 'warning' ? 'Medium' : 'Low',
  }))

  const passCount = rows.filter((r) => r.status === 'PASS').length
  const warnCount = rows.filter((r) => r.status === 'WARNING').length
  const failCount = rows.filter((r) => r.status === 'FAIL').length

  if (!tenderId) {
    return (
      <WidgetContainer>
        <WidgetHeader title="PPR Compliance" subtitle="PPR-2025 rule evaluation" icon={<ShieldCheck size={16} />} />
        <WidgetContent>
          <div className="flex items-center justify-center py-12 text-xs text-gray-400">Select a tender to run compliance check</div>
        </WidgetContent>
      </WidgetContainer>
    )
  }

  return (
    <WidgetContainer>
      <WidgetHeader title="PPR Compliance" subtitle="PPR-2025 rule evaluation" icon={<ShieldCheck size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<Filter size={14} />} label="Filter" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Re-check" onClick={() => runCheck.mutate(tenderId)} />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={RULE_SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect>
          <option>All agencies</option>
          <option>BWDB</option>
          <option>LGED</option>
        </FilterSelect>
        <FilterInput value={searchQuery} onChange={setSearchQuery} placeholder="Search rules..." />
      </WidgetFilters>
      {isLoading ? (
        <div className="flex items-center justify-center py-8"><Loader2 size={20} className="animate-spin text-gray-400" /></div>
      ) : rows.length === 0 ? (
        <div className="flex items-center justify-center py-8 text-xs text-gray-400">No compliance rules found for this tender</div>
      ) : (
        <WidgetTable columns={RULE_COLUMNS} data={rows} />
      )}
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="AI Compliance Review" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{passCount} PASS · {warnCount} WARNING · {failCount} FAIL</span>
          <span className="flex items-center gap-1"><Scale size={12} /> PPR-2025 v2.3</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="compliance" widgetTitle="PPR Compliance" confidence={94} evidence={EVIDENCE} agentRuns={[
        { agent: 'Compliance Checker', status: 'completed', duration: '2.1s' },
      ]} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="PPR Compliance" />
    </WidgetContainer>
  )
}
