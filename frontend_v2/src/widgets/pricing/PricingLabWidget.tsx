import { useState, useMemo } from 'react'
import { DollarSign, TrendingUp, RefreshCw, Download, FileText, Filter } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterSelect, WidgetTable, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { Column, TrustEvidence, Tab, SubTab } from '@widgets/shared'
import { Badge } from '@shared/ui/Badge'
import { usePricingPrediction } from '@hooks/pricing'
import type { PricingPredictionParams } from '@entities/pricing/api'
import { usePricingScenarios, useRecentAgentRuns } from '@hooks/index'

const TABS: Tab[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'simulation', label: 'Simulation' },
  { id: 'materials', label: 'Materials' },
  { id: 'profit', label: 'Profit' },
  { id: 'discount', label: 'Discount' },
  { id: 'history', label: 'History' },
]

interface Row { id: string; discount: string; winPct: string; profit: string; rank: number; recommended?: boolean }

const DEFAULT_ROWS: Row[] = [
  { id: '1', discount: '7%', winPct: '71%', profit: '৳1.8 Cr', rank: 2 },
  { id: '2', discount: '8%', winPct: '76%', profit: '৳1.6 Cr', rank: 1, recommended: true },
  { id: '3', discount: '9%', winPct: '82%', profit: '৳1.3 Cr', rank: 3 },
  { id: '4', discount: '10%', winPct: '87%', profit: '৳1.1 Cr', rank: 4 },
]

const COLUMNS: Column<Row>[] = [
  { id: 'discount', header: 'Discount', accessor: (r) => <span className="font-medium text-gray-900 dark:text-white">{r.discount}</span> },
  { id: 'winPct', header: 'Win %', accessor: (r) => (<div className="flex items-center gap-2"><div className="h-1.5 w-12 rounded-full bg-gray-200 dark:bg-gray-700"><div className="h-full rounded-full bg-brand-500" style={{ width: r.winPct }} /></div><span>{r.winPct}</span></div>) },
  { id: 'profit', header: 'Profit', accessor: (r) => <span className="font-semibold text-green-600 dark:text-green-400">{r.profit}</span>, align: 'right' },
  { id: 'rank', header: 'Rank', accessor: (r) => (<span className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold ${r.rank === 1 ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/20 dark:text-brand-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'}`}>{r.rank}</span>), align: 'center' },
  { id: 'action', header: '', accessor: (r) => r.recommended ? <Badge>Recommended</Badge> : null, align: 'center' },
]

export interface PricingLabWidgetProps {
  tenderId?: string
  params?: PricingPredictionParams
}

export function PricingLabWidget({ tenderId, params }: PricingLabWidgetProps) {
  const [activeTab, setActiveTab] = useState('overview')
  const [activeSubTab, setActiveSubTab] = useState('recommended')
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data: prediction, isLoading } = usePricingPrediction(tenderId, params)
  const { data: scenariosData } = usePricingScenarios()
  const { data: runsRes } = useRecentAgentRuns(10)

  const SCENARIO_SUBTABS: SubTab[] = useMemo(() => {
    if (scenariosData?.scenarios) return Object.entries(scenariosData.scenarios).map(([id, scenario]) => ({ id, label: scenario.label }))
    return [{ id: 'safe', label: 'Safe' }, { id: 'recommended', label: 'Recommended' }, { id: 'aggressive', label: 'Aggressive' }, { id: 'custom', label: 'Custom' }]
  }, [scenariosData])

  const EVIDENCE: TrustEvidence[] = useMemo(() => {
    const items: TrustEvidence[] = [{ id: 'ev-1', label: 'Pricing model based on 12-mo history', status: 'verified', detail: 'Bayesian win probability model' }]
    if (runsRes?.length) items.push(...runsRes.slice(0, 2).map((r, i) => ({ id: `ev-${i + 2}`, label: `${r.agent_name ?? r.agent_id} run`, status: r.status === 'success' ? 'verified' as const : 'warning' as const, detail: r.status })))
    return items
  }, [runsRes])

  const rows: Row[] = useMemo(() => {
    if (!prediction) return DEFAULT_ROWS
    const discounts = [7, 8, 9, 10]
    const baseProfit = prediction.expected_profit
    return discounts.map((d, i) => {
      const winAdj = d <= prediction.discount_percent ? 0.75 + d * 0.02 : 0.65 + d * 0.015
      const winPct = Math.min(Math.round(winAdj * 100), 95)
      const profitRatio = 1 - (d - prediction.discount_percent) * 0.05
      const profit = baseProfit * profitRatio
      const fmtProfit = profit >= 1e7 ? `৳${(profit / 1e7).toFixed(1)} Cr` : `৳${(profit / 1e5).toFixed(1)}L`
      return {
        id: String(i + 1),
        discount: `${d}%`,
        winPct: `${winPct}%`,
        profit: fmtProfit,
        rank: i + 1,
        recommended: d === prediction.discount_percent,
      }
    }).sort((a, b) => b.rank - a.rank).map((r, i) => ({ ...r, rank: i + 1 }))
  }, [prediction])

  const recommendedRow = useMemo(() => rows.find((r) => r.recommended), [rows])

  return (
    <WidgetContainer>
      <WidgetHeader title="Pricing Lab" subtitle="Scenario simulation & optimization" icon={<DollarSign size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<RefreshCw size={14} />} label="Recalculate" />
        <ToolbarButton icon={<FileText size={14} />} label="Save Strategy" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
        <ToolbarButton icon={<Filter size={14} />} label="Parameters" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SCENARIO_SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect label="Base markup"><option>15%</option><option>18%</option><option>20%</option></FilterSelect>
        <FilterSelect label="Risk adj."><option>None</option><option>Low</option><option>Medium</option><option>High</option></FilterSelect>
      </WidgetFilters>
      {isLoading ? (
        <div className="flex items-center justify-center h-32"><p className="text-sm text-gray-500">Calculating pricing scenarios...</p></div>
      ) : (
        <WidgetTable columns={COLUMNS} data={rows} />
      )}
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Optimize Pricing" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{recommendedRow ? `Recommended: ${recommendedRow.discount} discount · ${recommendedRow.winPct} win probability` : 'Recommended: 8% discount · 76% win probability'}</span>
          <span className="flex items-center gap-1"><TrendingUp size={12} /> Expected: {recommendedRow ? recommendedRow.profit : '৳1.6 Cr'}</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="pricing-lab" widgetTitle="Pricing Lab" confidence={prediction ? Math.round(prediction.confidence * 100) : 88} evidence={EVIDENCE} agentRuns={[
        { agent: 'Pricing Optimizer', status: 'completed', duration: '0.8s' },
      ]} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Pricing Lab" />
    </WidgetContainer>
  )
}
