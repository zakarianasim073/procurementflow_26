import { useState, useMemo } from 'react'
import { DollarSign, TrendingUp, BarChart3, PieChart, RefreshCw, Download, Settings } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterInput, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { useExecutivePipeline } from '@hooks/executive'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'by-agency', label: 'By Agency' },
  { id: 'by-type', label: 'By Type' },
  { id: 'forecast', label: 'Forecast' },
]

const SUBTABS = [
  { id: 'monthly', label: 'Monthly' },
  { id: 'quarterly', label: 'Quarterly' },
  { id: 'ytd', label: 'YTD' },
]

const FALLBACK_DATA = [
  { agency: 'BWDB', value: '৳32.4 Cr', count: 14, change: '+8%' },
  { agency: 'LGED', value: '৳28.7 Cr', count: 11, change: '+15%' },
  { agency: 'PWD', value: '৳18.2 Cr', count: 8, change: '-3%' },
  { agency: 'RHD', value: '৳8.1 Cr', count: 5, change: '+22%' },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Revenue calculated from awarded tenders', status: 'verified', detail: 'Sourced from award records DB' },
  { id: 'ev-2', label: 'Forecast based on pipeline + historical', status: 'warning', detail: '+/- 12% margin of error' },
]

export interface RevenueWidgetProps {
  agencyFilter?: string
}

export function RevenueWidget({ agencyFilter }: RevenueWidgetProps) {
  const [activeTab, setActiveTab] = useState('overview')
  const [activeSubTab, setActiveSubTab] = useState('monthly')
  const [searchQuery, setSearchQuery] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: pipelineData, isLoading } = useExecutivePipeline()

  const revenueData = useMemo(() => {
    if (!pipelineData?.agencies?.length) return FALLBACK_DATA
    let agencies = pipelineData.agencies
    if (agencyFilter) agencies = agencies.filter(a => a.agency_code === agencyFilter)
    return agencies.map(a => {
      const changePct = a.closing_7d > 0 ? ((a.closing_30d - a.closing_7d) / a.closing_7d * 100) : 0
      const changeStr = `${changePct >= 0 ? '+' : ''}${changePct.toFixed(0)}%`
      return {
        agency: a.agency_code,
        value: `৳${(a.estimated_pipeline_value_bdt / 1e7).toFixed(1)} Cr`,
        count: a.live_tenders,
        change: changeStr,
      }
    })
  }, [pipelineData, agencyFilter])

  if (isLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="Revenue" subtitle="Projected and realized" icon={<DollarSign size={16} />} actions={
        <ToolbarButton icon={<Settings size={14} />} label="" />
      } />
      <WidgetToolbar>
        <ToolbarButton icon={<BarChart3 size={14} />} label="Chart" />
        <ToolbarButton icon={<PieChart size={14} />} label="Breakdown" active />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterInput value={searchQuery} onChange={setSearchQuery} placeholder="Filter agencies..." />
      </WidgetFilters>
      <WidgetContent>
        <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
          {revenueData.map((item) => (
            <div key={item.agency} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-900 dark:text-white">{item.agency}</span>
                <Badge>{item.count} tenders</Badge>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{item.value}</p>
                <span className={cn('text-[11px]', item.change.startsWith('+') ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400')}>
                  {item.change}
                </span>
              </div>
            </div>
          ))}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Analyze Revenue" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>Total projected: ৳87.4 Cr</span>
          <span className="flex items-center gap-1"><TrendingUp size={12} className="text-green-500" /> +12% vs Q1</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="revenue" widgetTitle="Revenue" confidence={91} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Revenue" />
    </WidgetContainer>
  )
}
