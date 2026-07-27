import { useState, useMemo } from 'react'
import { Users, Award, TrendingDown, Activity, ArrowRight, Search, RefreshCw, Download } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterInput, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { useCompetitors } from '@hooks/competitor'

const TABS = [
  { id: 'all', label: 'All', count: 4 },
  { id: 'new', label: 'New Bids', count: 2 },
  { id: 'awards', label: 'Awards', count: 1 },
  { id: 'pricing', label: 'Pricing', count: 1 },
]

const SUBTABS = [
  { id: 'bwdb', label: 'BWDB' },
  { id: 'lged', label: 'LGED' },
  { id: 'pwd', label: 'PWD' },
  { id: 'rhd', label: 'RHD' },
]

const FALLBACK_ALERTS = [
  { id: '1', competitor: 'ABC Construction Ltd', type: 'new-bid' as const, tender: 'BWDB-24/2026', value: '৳2.1 Cr', time: 'Today' },
  { id: '2', competitor: 'XYZ Engineers', type: 'award' as const, tender: 'LGED-19/2026', value: '৳1.5 Cr', time: 'Yesterday' },
  { id: '3', competitor: 'Delta Builders', type: 'pricing' as const, tender: 'PWD-07/2026', detail: '8.2% discount detected', time: '2d ago' },
  { id: '4', competitor: 'Modern Construction', type: 'new-bid' as const, tender: 'RHD-03/2026', value: '৳0.8 Cr', time: '3d ago' },
]

const TYPE_STYLES = { 'new-bid': { icon: Activity, label: 'New Bid', color: 'text-blue-500', bg: 'bg-blue-50' }, award: { icon: Award, label: 'Award', color: 'text-green-500', bg: 'bg-green-50' }, pricing: { icon: TrendingDown, label: 'Pricing', color: 'text-amber-500', bg: 'bg-amber-50' } }

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Competitor tracking from e-GP awards', status: 'verified', detail: '87 competitors tracked' },
]

export interface CompetitorAlertsWidgetProps {
  searchQuery?: string
}

export function CompetitorAlertsWidget({ searchQuery: externalSearch }: CompetitorAlertsWidgetProps) {
  const [activeTab, setActiveTab] = useState('all')
  const [activeSubTab, setActiveSubTab] = useState('bwdb')
  const [internalSearch, setInternalSearch] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: competitors, isLoading } = useCompetitors({ limit: 50 })

  const searchQuery = externalSearch ?? internalSearch

  const alerts = useMemo(() => {
    if (!competitors?.length) return FALLBACK_ALERTS
    const items = competitors.flatMap(c =>
      (c.recent_activity ?? []).map((act, idx) => ({
        id: `${c.competitor_id}-${idx}`,
        competitor: c.name,
        type: (act.status === 'won' ? 'award' : act.status === 'submitted' ? 'new-bid' : 'pricing') as 'new-bid' | 'award' | 'pricing',
        tender: act.title ?? act.tender_id,
        value: act.bid_amount ? `৳${(act.bid_amount / 1e7).toFixed(1)} Cr` : undefined,
        detail: act.status === 'lost' ? 'Lost bid' : undefined,
        time: timeAgo(act.date),
      }))
    )
    return items.slice(0, 10)
  }, [competitors])

  const filteredAlerts = alerts.filter(a => !searchQuery || a.competitor.toLowerCase().includes(searchQuery.toLowerCase()))

  if (isLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="Competitor Alerts" subtitle="Market activity tracking" icon={<Users size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
        <ToolbarButton icon={<ArrowRight size={14} />} label="View All" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterInput value={searchQuery} onChange={setInternalSearch} placeholder="Search competitors..." />
      </WidgetFilters>
      <WidgetContent>
        <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
          {filteredAlerts.map((alert) => {
            const style = TYPE_STYLES[alert.type as keyof typeof TYPE_STYLES]
            const Icon = style.icon
            return (
              <div key={alert.id} className="flex items-start gap-3 px-4 py-3">
                <div className={cn('rounded-lg p-1.5', style.bg)}><Icon size={14} className={style.color} /></div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-900 dark:text-white">{alert.competitor}</span>
                    <Badge variant="outline" className="text-[10px]">{style.label}</Badge>
                  </div>
                  <p className="mt-0.5 text-[11px] text-gray-500">{alert.tender}{alert.value ? ` · ${alert.value}` : ''}{alert.detail ? ` · ${alert.detail}` : ''}</p>
                </div>
                <span className="shrink-0 text-[10px] text-gray-400">{alert.time}</span>
              </div>
            )
          })}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Competitor Intel" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>4 competitor events this week</span>
          <span className="text-brand-600 text-[11px]">View all competitors</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="competitor-alerts" widgetTitle="Competitor Alerts" confidence={87} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Competitor Alerts" />
    </WidgetContainer>
  )
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
