import { useState, useMemo } from 'react'
import { Brain, Lightbulb, TrendingUp, AlertTriangle, CheckCircle, X, Search, RefreshCw, Download } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterInput, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { usePredictionsModelStatus } from '@hooks/executive'

const TABS = [
  { id: 'all', label: 'All', count: 4 },
  { id: 'opportunities', label: 'Opportunities', count: 2 },
  { id: 'risks', label: 'Risks', count: 1 },
  { id: 'recommendations', label: 'Recommendations', count: 1 },
]

const SUBTABS = [
  { id: 'today', label: 'Today' },
  { id: 'week', label: 'This Week' },
  { id: 'month', label: 'This Month' },
]

const FALLBACK_INSIGHTS = [
  { id: '1', type: 'opportunity' as const, title: 'High-value BWDB tender detected', description: 'BWDB-24/2026 has 86% match. Value ৳2.1 Cr.', impact: 'positive' as const, time: '2h ago' },
  { id: '2', type: 'risk' as const, title: 'Margin pressure on LGED-18', description: '3 new competitors. Recommended 8.5% discount.', impact: 'negative' as const, time: '4h ago' },
  { id: '3', type: 'recommendation' as const, title: 'Capacity reallocation suggested', description: 'Project XYZ completes next week.', impact: 'positive' as const, time: '1d ago' },
  { id: '4', type: 'opportunity' as const, title: 'PWD zoning change detected', description: 'New circular allows expanded Zone C scope.', impact: 'positive' as const, time: '1d ago' },
]

const TYPE_STYLES = { opportunity: { icon: TrendingUp, color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/10' }, risk: { icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/10' }, recommendation: { icon: Lightbulb, color: 'text-amber-500', bg: 'bg-amber-50 dark:bg-amber-900/10' } }

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'AI model v2.4 analysis', status: 'verified', detail: 'Trained on 12 months of procurement data' },
  { id: 'ev-2', label: 'Market data from e-GP crawl', status: 'verified', detail: 'Last crawl 10 min ago' },
]

export function AIInsightsWidget() {
  const [activeTab, setActiveTab] = useState('all')
  const [activeSubTab, setActiveSubTab] = useState('today')
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: modelStatus, isLoading } = usePredictionsModelStatus()

  const insights = useMemo(() => {
    if (!modelStatus) return FALLBACK_INSIGHTS
    const items = [
      { id: 'model-1', type: 'recommendation' as const, title: `Tender Price Model: ${modelStatus.tender_price_model.name}`, description: `Version: ${modelStatus.tender_price_model.version ?? 'N/A'} · Trained: ${modelStatus.tender_price_model.trained_at ?? 'Never'}`, impact: 'positive' as const, time: 'Live' },
      { id: 'model-2', type: 'recommendation' as const, title: `Bid Price Model: ${modelStatus.bid_price_model.name}`, description: `Version: ${modelStatus.bid_price_model.version ?? 'N/A'} · Trained: ${modelStatus.bid_price_model.trained_at ?? 'Never'}`, impact: 'positive' as const, time: 'Live' },
    ]
    return items
  }, [modelStatus])

  const filtered = insights.filter((i) => activeTab === 'all' || i.type === activeTab).filter((i) => !dismissed.has(i.id))

  if (isLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="AI Insights" subtitle="Intelligent recommendations" icon={<Brain size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterInput value="" onChange={() => {}} placeholder="Search insights..." />
      </WidgetFilters>
      <WidgetContent>
        <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
          {filtered.map((insight) => {
            const style = TYPE_STYLES[insight.type as keyof typeof TYPE_STYLES]
            const Icon = style.icon
            return (
              <div key={insight.id} className="group relative px-4 py-3 transition-colors hover:bg-gray-50/50 dark:hover:bg-gray-800/20">
                <button type="button" onClick={() => setDismissed(new Set(dismissed).add(insight.id))} className="absolute right-3 top-3 opacity-0 transition-opacity group-hover:opacity-100">
                  <X size={12} className="text-gray-400 hover:text-gray-600" />
                </button>
                <div className="flex items-start gap-3">
                  <div className={cn('rounded-lg p-1.5', style.bg)}><Icon size={14} className={style.color} /></div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium text-gray-900 dark:text-white">{insight.title}</p>
                      <Badge variant="outline" className="text-[10px]">{insight.type}</Badge>
                    </div>
                    <p className="mt-0.5 text-[11px] text-gray-500">{insight.description}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Deep Dive" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{filtered.length} active insights</span>
          <span className="flex items-center gap-1"><CheckCircle size={12} /> AI confidence: 94%</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="ai-insights" widgetTitle="AI Insights" confidence={94} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="AI Insights" />
    </WidgetContainer>
  )
}
