import { useState } from 'react'
import { Users, Activity, Search, RefreshCw, Download, Filter, Loader2 } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterInput, FilterSelect, WidgetTable, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { Column, TrustEvidence, Tab, SubTab } from '@widgets/shared'
import { Progress } from '@shared/ui/Progress'
import { useCompetitors } from '@hooks/index'

const TABS: Tab[] = [
  { id: 'profiles', label: 'Profiles' },
  { id: 'history', label: 'History' },
  { id: 'awards', label: 'Awards' },
  { id: 'discount', label: 'Discount' },
  { id: 'strengths', label: 'Strengths' },
  { id: 'weaknesses', label: 'Weaknesses' },
]

const AGENCY_SUBTABS: SubTab[] = [
  { id: 'bwdb', label: 'BWDB' }, { id: 'lged', label: 'LGED' },
  { id: 'rhd', label: 'RHD' }, { id: 'pwd', label: 'PWD' },
]

interface Row { id: string; company: string; winRate: string; avgDiscount: string; awards: number; trend: 'up' | 'down' | 'stable' }

const TREND_ICONS = { up: '▲', down: '▼', stable: '→' }
const TREND_COLORS = { up: 'text-green-500', down: 'text-red-500', stable: 'text-gray-400' }

const COLUMNS: Column<Row>[] = [
  { id: 'company', header: 'Company', accessor: (r) => <span className="font-medium text-gray-900 dark:text-white">{r.company}</span> },
  { id: 'winRate', header: 'Win Rate', accessor: (r) => (<div className="flex items-center gap-2"><Progress value={parseInt(r.winRate)} className="h-1.5 w-12" /><span className="font-medium">{r.winRate}</span></div>) },
  { id: 'avgDiscount', header: 'Avg Discount', accessor: (r) => r.avgDiscount, align: 'center' },
  { id: 'awards', header: 'Awards', accessor: (r) => <span className="font-semibold">{r.awards}</span>, align: 'right' },
  { id: 'trend', header: 'Trend', accessor: (r) => <span className={`font-medium ${TREND_COLORS[r.trend]}`}>{TREND_ICONS[r.trend]} {r.trend}</span>, align: 'center' },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Competitor data from e-GP awards', status: 'verified', detail: '32K contractor records analyzed' },
  { id: 'ev-2', label: 'Discount patterns from bid data', status: 'verified', detail: 'Historical bid analysis' },
]

export function CompetitorWidget() {
  const [activeTab, setActiveTab] = useState('profiles')
  const [activeSubTab, setActiveSubTab] = useState('bwdb')
  const [search, setSearch] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data: competitors, isLoading } = useCompetitors({ search })

  const rows: Row[] = (competitors ?? []).map((c) => {
    const winRate = c.win_rate ?? (c.total_bids > 0 ? Math.round((c.total_wins / c.total_bids) * 100) : 0)
    const recentWon = c.recent_activity?.filter((a) => a.status === 'won').length ?? 0
    const recentLost = c.recent_activity?.filter((a) => a.status === 'lost').length ?? 0
    const trend: Row['trend'] = recentWon > recentLost ? 'up' : recentLost > recentWon ? 'down' : 'stable'
    return {
      id: c.competitor_id ?? c.name,
      company: c.name,
      winRate: `${winRate}%`,
      avgDiscount: c.avg_discount ? `${c.avg_discount.toFixed(1)}%` : '-',
      awards: c.total_wins ?? 0,
      trend,
    }
  })

  return (
    <WidgetContainer>
      <WidgetHeader title="Competitor Intelligence" subtitle="Market competitive landscape" icon={<Users size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<Filter size={14} />} label="Filter" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={AGENCY_SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterInput value={search} onChange={setSearch} placeholder="Search competitors..." />
        <FilterSelect><option>All zones</option><option>Zone A</option><option>Zone B</option><option>Zone C</option><option>Zone D</option></FilterSelect>
      </WidgetFilters>
      {isLoading ? (
        <div className="flex items-center justify-center py-8"><Loader2 size={20} className="animate-spin text-gray-400" /></div>
      ) : rows.length === 0 ? (
        <div className="flex items-center justify-center py-8 text-xs text-gray-400">No competitor data available</div>
      ) : (
        <WidgetTable columns={COLUMNS} data={rows} />
      )}
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Competitor Analysis" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{rows.length} competitors tracked</span>
          <span className="flex items-center gap-1"><Activity size={12} /> {rows.filter((r) => r.trend === 'up').length} rising</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="competitor" widgetTitle="Competitor Intel" confidence={87} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Competitor Intel" />
    </WidgetContainer>
  )
}