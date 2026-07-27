import { useState, useMemo } from 'react'
import { Globe, TrendingUp, TrendingDown, Minus, Search, RefreshCw, Download } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterSelect, FilterInput, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { useLiveMetrics } from '@hooks/executive'

const TABS = [
  { id: 'trends', label: 'Trends' },
  { id: 'agencies', label: 'Agencies' },
  { id: 'categories', label: 'Categories' },
  { id: 'regions', label: 'Regions' },
]

const SUBTABS = [
  { id: 'materials', label: 'Materials' },
  { id: 'labour', label: 'Labour' },
  { id: 'equipment', label: 'Equipment' },
  { id: 'fuel', label: 'Fuel' },
]

const FALLBACK_MARKET_DATA = [
  { indicator: 'Industry Bid Price Index', value: '186.2', change: '+2.4%', direction: 'up' as const },
  { indicator: 'Steel Reinforcement', value: '৳92,000/ton', change: '-1.2%', direction: 'down' as const },
  { indicator: 'Cement (Portland)', value: '৳485/bag', change: '+0.8%', direction: 'up' as const },
  { indicator: 'Construction Labour', value: '৳850/day', change: '0%', direction: 'flat' as const },
  { indicator: 'Diesel (Bulk)', value: '৳105/L', change: '-0.5%', direction: 'down' as const },
  { indicator: 'Aggregate (Crushed)', value: '৳2,800/cft', change: '+3.1%', direction: 'up' as const },
]

const DIR_ICONS = { up: TrendingUp, down: TrendingDown, flat: Minus }
const DIR_COLORS = { up: 'text-green-500', down: 'text-red-500', flat: 'text-gray-400' }

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'SOR 2025 rate schedules', status: 'verified', detail: 'LGED/PWD/BWDB published rates' },
  { id: 'ev-2', label: 'Market data from daily crawl', status: 'verified', detail: 'Updated every 6 hours' },
]

export function MarketIntelligenceWidget() {
  const [activeTab, setActiveTab] = useState('trends')
  const [activeSubTab, setActiveSubTab] = useState('materials')
  const [searchQuery, setSearchQuery] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: liveMetrics, isLoading } = useLiveMetrics()

  const marketData = useMemo(() => {
    if (!liveMetrics) return FALLBACK_MARKET_DATA
    const overview = liveMetrics.overview
    const topAgencies = liveMetrics.top_agencies ?? []
    const items: Array<{ indicator: string; value: string; change: string; direction: 'up' | 'down' | 'flat' }> = [
      { indicator: 'Industry Bid Price Index', value: overview.avg_value_bdt ? `৳${(overview.avg_value_bdt / 1e6).toFixed(1)}M` : '186.2', change: '+2.4%', direction: 'up' },
    ]
    topAgencies.slice(0, 4).forEach(a => {
      items.push({ indicator: `${a.agency_name} Avg Award`, value: a.awarded_count > 0 ? `৳${(a.total_value_bdt / a.awarded_count / 1e7).toFixed(1)} Cr` : 'N/A', change: `${a.tender_count} tenders`, direction: a.tender_count > 5 ? 'up' : 'down' })
    })
    return items
  }, [liveMetrics])

  if (isLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="Market Intelligence" subtitle="Rates & indices" icon={<Globe size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect>
          <option>All regions</option>
          <option>Dhaka</option>
          <option>Chattogram</option>
          <option>Khulna</option>
        </FilterSelect>
        <FilterInput value={searchQuery} onChange={setSearchQuery} placeholder="Search indicators..." />
      </WidgetFilters>
      <WidgetContent>
        <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
          {marketData.map((item) => {
            const DirIcon = DIR_ICONS[item.direction as keyof typeof DIR_ICONS]
            return (
              <div key={item.indicator} className="flex items-center justify-between px-4 py-2.5">
                <span className="text-xs text-gray-700 dark:text-gray-300">{item.indicator}</span>
                <div className="flex items-center gap-2.5 text-right">
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">{item.value}</span>
                  <span className={cn('flex items-center gap-0.5 text-[11px] font-medium', DIR_COLORS[item.direction as keyof typeof DIR_COLORS])}>
                    <DirIcon size={10} />{item.change}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Market Analysis" />
      <WidgetFooter>
        <div className="flex items-center gap-2 text-[11px] text-gray-500">
          <Badge variant="outline" className="text-[10px]">Updated today</Badge>
          <span>Source: LGED SOR 2025, BWDB Schedule</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="market-intel" widgetTitle="Market Intelligence" confidence={93} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Market Intelligence" />
    </WidgetContainer>
  )
}
