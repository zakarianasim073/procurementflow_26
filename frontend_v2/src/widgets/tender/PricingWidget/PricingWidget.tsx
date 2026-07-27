import { useState, useMemo } from 'react'
import { DollarSign, BarChart3, RefreshCw, Download } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence, Tab } from '@widgets/shared'
import { usePricingPrediction } from '@hooks/pricing'
import type { PricingPredictionParams } from '@entities/pricing/api'

const TABS: Tab[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'scenarios', label: 'Scenarios' },
  { id: 'history', label: 'History' },
  { id: 'optimize', label: 'Optimize' },
  { id: 'compare', label: 'Compare' },
  { id: 'report', label: 'Report' },
]

const SCENARIO_TABS: Tab[] = [
  { id: 'aggressive', label: 'Aggressive' },
  { id: 'moderate', label: 'Moderate' },
  { id: 'conservative', label: 'Conservative' },
  { id: 'custom', label: 'Custom' },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Pricing from SOR rates + market data', status: 'verified', detail: 'BWDB 2026' },
]

export interface PricingWidgetProps {
  tenderId?: string
  params?: PricingPredictionParams
}

export function PricingWidget({ tenderId, params }: PricingWidgetProps) {
  const [activeTab, setActiveTab] = useState('overview')
  const [scenarioTab, setScenarioTab] = useState('moderate')
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data: prediction, isLoading } = usePricingPrediction(tenderId, params)

  const overviewItems = useMemo(() => {
    if (prediction) {
      const fmt = (n: number) => `৳ ${(n / 1e5).toFixed(1)}L`
      return [
        { label: 'Bid Price', value: fmt(prediction.bid_price), trend: 'up' as const },
        { label: 'Margin', value: `${prediction.margin_percent.toFixed(1)}%`, trend: 'up' as const },
        { label: 'Win Probability', value: `${(prediction.win_probability * 100).toFixed(0)}%`, trend: 'up' as const },
      ]
    }
    return [
      { label: 'Bid Price', value: '৳ 8,45,00,000', trend: 'up' as const },
      { label: 'Margin', value: '12.4%', trend: 'up' as const },
      { label: 'Win Probability', value: '78%', trend: 'up' as const },
    ]
  }, [prediction])

  return (
    <WidgetContainer>
      <WidgetHeader title="Pricing Lab" subtitle="Bid price strategy & optimization" icon={<DollarSign size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<BarChart3 size={14} />} label="Scenario" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SCENARIO_TABS} activeSubTab={scenarioTab} onSubTabChange={setScenarioTab} />
      <WidgetContent>
        <div className="p-4 space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center h-24"><p className="text-sm text-gray-500">Calculating pricing...</p></div>
          ) : (
            <div className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
              <p className="text-[11px] font-medium text-gray-500 mb-2">Scenario: {scenarioTab.charAt(0).toUpperCase() + scenarioTab.slice(1)}</p>
              <div className="grid grid-cols-3 gap-4">
                {overviewItems.map(({ label, value, trend }) => (
                  <div key={label} className="text-center">
                    <p className="text-[10px] text-gray-400">{label}</p>
                    <p className="text-sm font-bold text-gray-900 dark:text-white">{value}</p>
                    <span className={`text-[10px] ${trend === 'up' ? 'text-green-500' : 'text-red-500'}`}>{trend === 'up' ? '▲' : '▼'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Optimize Pricing" />
      <WidgetFooter>
        <div className="text-[11px] text-gray-500">{prediction ? `Confidence: ${(prediction.confidence * 100).toFixed(0)}% · ${prediction.reasoning}` : 'Last price analysis: 10 min ago'}</div>
      </WidgetFooter>
      <TrustPanel widgetId="pricing" widgetTitle="Pricing Lab" confidence={prediction ? Math.round(prediction.confidence * 100) : 90} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Pricing Lab" />
    </WidgetContainer>
  )
}
