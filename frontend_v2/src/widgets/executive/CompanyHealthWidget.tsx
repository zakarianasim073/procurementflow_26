import { useState, useMemo } from 'react'
import { Activity, CheckCircle, AlertTriangle, XCircle, Search, RefreshCw, Settings } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterSelect, FilterInput, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Progress } from '@shared/ui/Progress'
import { useExecutiveOverview } from '@hooks/executive'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'financial', label: 'Financial' },
  { id: 'capacity', label: 'Capacity' },
  { id: 'compliance', label: 'Compliance' },
]

const SUBTABS = [
  { id: 'summary', label: 'Summary' },
  { id: 'trends', label: 'Trends' },
  { id: 'benchmark', label: 'Benchmark' },
]

const FALLBACK_METRICS = [
  { label: 'Financial Health', score: 82, status: 'good', detail: 'Stable cash flow, low debt ratio' },
  { label: 'Capacity Utilization', score: 68, status: 'warning', detail: '3 projects at 70% capacity' },
  { label: 'Compliance Score', score: 94, status: 'good', detail: 'All certifications valid' },
  { label: 'Win Rate Trend', score: 45, status: 'warning', detail: 'Declining over last 2 quarters' },
]

const STATUS_ICONS = { good: CheckCircle, warning: AlertTriangle, critical: XCircle }
const STATUS_COLORS = { good: 'text-green-500', warning: 'text-amber-500', critical: 'text-red-500' }

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Financial data from audited statements', status: 'verified', detail: 'Q2 2026 audit completed' },
  { id: 'ev-2', label: 'Capacity from resource planning tool', status: 'warning', detail: 'Last sync 2h ago' },
]

export function CompanyHealthWidget() {
  const [activeTab, setActiveTab] = useState('overview')
  const [activeSubTab, setActiveSubTab] = useState('summary')
  const [searchQuery, setSearchQuery] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: overview, isLoading } = useExecutiveOverview()

  const healthMetrics = useMemo(() => {
    if (!overview) return FALLBACK_METRICS
    const execution = overview.execution
    const agents = overview.agents
    const totalValue = execution.eexperience_value_bdt + execution.ecms_value_bdt
    const financialScore = totalValue > 0 ? Math.min(Math.round((execution.eexperience_value_bdt / totalValue) * 100), 100) : 82
    const capacityScore = agents.total > 0 ? Math.round((agents.active / agents.total) * 100) : 68
    return [
      { label: 'Financial Health', score: financialScore, status: (financialScore >= 70 ? 'good' : financialScore >= 50 ? 'warning' : 'critical') as 'good' | 'warning' | 'critical', detail: `Value: ৳${(totalValue / 1e7).toFixed(1)} Cr` },
      { label: 'Capacity Utilization', score: capacityScore, status: (capacityScore >= 70 ? 'good' : capacityScore >= 50 ? 'warning' : 'critical') as 'good' | 'warning' | 'critical', detail: `${agents.active} of ${agents.total} agents active` },
      { label: 'Compliance Score', score: 94, status: 'good', detail: 'All certifications valid' },
      { label: 'Win Rate Trend', score: 45, status: 'warning', detail: 'Declining over last 2 quarters' },
    ]
  }, [overview])

  if (isLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="Company Health" subtitle="Organizational performance" icon={<Activity size={16} />} actions={
        <ToolbarButton icon={<Settings size={14} />} label="" />
      } />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect>
          <option>All departments</option>
          <option>Engineering</option>
          <option>Finance</option>
        </FilterSelect>
        <FilterInput value={searchQuery} onChange={setSearchQuery} placeholder="Filter..." />
      </WidgetFilters>
      <WidgetContent>
        <div className="space-y-3 p-4">
          {healthMetrics.map((m) => {
            const StatusIcon = STATUS_ICONS[m.status as keyof typeof STATUS_ICONS]
            return (
              <div key={m.label} className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <StatusIcon size={14} className={STATUS_COLORS[m.status as keyof typeof STATUS_COLORS]} />
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{m.label}</span>
                  </div>
                  <span className={cn('text-sm font-bold', m.score >= 70 ? 'text-green-600' : m.score >= 50 ? 'text-amber-600' : 'text-red-600')}>
                    {m.score}%
                  </span>
                </div>
                <Progress value={m.score} className="mt-2 h-1.5" />
                <p className="mt-1.5 text-[11px] text-gray-500">{m.detail}</p>
              </div>
            )
          })}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Health Analysis" />
      <WidgetFooter>
        <div className="text-[11px] text-gray-500">Overall health score: 72% · 2 areas need attention</div>
      </WidgetFooter>
      <TrustPanel widgetId="company-health" widgetTitle="Company Health" confidence={89} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Company Health" />
    </WidgetContainer>
  )
}
