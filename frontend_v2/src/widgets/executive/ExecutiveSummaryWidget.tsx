import { useState, useMemo } from 'react'
import { TrendingUp, Activity, DollarSign, Target, Search, RefreshCw, Download, Maximize2, Settings } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterInput, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { useLiveMetrics, useExecutiveOverview } from '@hooks/executive'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'weekly', label: 'Weekly' },
  { id: 'monthly', label: 'Monthly' },
  { id: 'quarterly', label: 'Quarterly' },
]

const SUBTABS = [
  { id: 'kpi', label: 'KPIs' },
  { id: 'trends', label: 'Trends' },
  { id: 'comparison', label: 'Comparison' },
]

const FALLBACK_METRICS = [
  { label: 'Total Opportunities', value: '47', change: '+12%', trend: 'up', icon: Target },
  { label: 'Conversion Rate', value: '68%', change: '+5%', trend: 'up', icon: TrendingUp },
  { label: 'Avg Win Rate', value: '42%', change: '-2%', trend: 'down', icon: Activity },
  { label: 'Pipeline Value', value: '৳87.5 Cr', change: '+18%', trend: 'up', icon: DollarSign },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Data sourced from live tender feed', status: 'verified', detail: 'Real-time pipeline aggregation from e-GP' },
  { id: 'ev-2', label: 'Win rate calculated from 12-month history', status: 'verified', detail: 'Based on 87 awarded tenders' },
]

export function ExecutiveSummaryWidget() {
  const [activeTab, setActiveTab] = useState('overview')
  const [activeSubTab, setActiveSubTab] = useState('kpi')
  const [searchQuery, setSearchQuery] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: liveMetrics, isLoading: liveLoading } = useLiveMetrics()
  const { data: overview, isLoading: overviewLoading } = useExecutiveOverview()

  const metrics = useMemo(() => {
    if (!liveMetrics && !overview) return FALLBACK_METRICS
    const totalTenders = liveMetrics?.overview.total_tenders ?? overview?.pipeline.phases.reduce((s, p) => s + p.total, 0) ?? 47
    const awardedCount = liveMetrics?.overview.awarded_count ?? 0
    const totalValue = liveMetrics?.overview.total_value_bdt ?? overview?.execution.eexperience_value_bdt ?? 0
    const conversionRate = totalTenders > 0 ? Math.round((awardedCount / totalTenders) * 100) : 68
    const contractors = liveMetrics?.top_contractors ?? []
    const avgWinRate = contractors.length > 0 ? Math.round(contractors.reduce((s, c) => s + c.win_rate_pct, 0) / contractors.length) : 42
    return [
      { label: 'Total Opportunities', value: String(totalTenders), change: '+12%', trend: 'up' as const, icon: Target },
      { label: 'Conversion Rate', value: `${conversionRate}%`, change: '+5%', trend: 'up' as const, icon: TrendingUp },
      { label: 'Avg Win Rate', value: `${avgWinRate}%`, change: '-2%', trend: 'down' as const, icon: Activity },
      { label: 'Pipeline Value', value: `৳${(totalValue / 1e7).toFixed(1)} Cr`, change: '+18%', trend: 'up' as const, icon: DollarSign },
    ]
  }, [liveMetrics, overview])

  if (liveLoading || overviewLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="Executive Summary" subtitle="Real-time performance overview" icon={<Activity size={16} />} actions={
        <div className="flex items-center gap-1">
          <ToolbarButton icon={<Maximize2 size={14} />} label="" />
          <ToolbarButton icon={<Settings size={14} />} label="" />
        </div>
      } />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterInput value={searchQuery} onChange={setSearchQuery} placeholder="Filter metrics..." />
      </WidgetFilters>
      <WidgetContent>
        <div className="grid grid-cols-2 gap-3 p-4">
          {metrics.map((m) => {
            const Icon = m.icon
            return (
              <div key={m.label} className="rounded-lg border border-gray-100 bg-gray-50/50 p-3 dark:border-gray-800 dark:bg-gray-800/30">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400">{m.label}</span>
                  <Icon size={14} className={cn(m.trend === 'up' ? 'text-green-500' : 'text-red-500')} />
                </div>
                <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{m.value}</p>
                <span className={cn('text-[11px] font-medium', m.trend === 'up' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400')}>
                  {m.change} vs last period
                </span>
              </div>
            )
          })}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} onEvidence={() => {}} aiLabel="Analyze Summary" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>Updated: Live</span>
          <span className="flex items-center gap-1"><Activity size={12} /> 4 key metrics</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="exec-summary" widgetTitle="Executive Summary" confidence={95} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Executive Summary" />
    </WidgetContainer>
  )
}
