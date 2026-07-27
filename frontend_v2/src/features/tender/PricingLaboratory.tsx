import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { ScreenTemplate } from '@layouts/index'
import {
  DiscountSlider,
  ProfitMarginDisplay,
  ExpectedValueCard,
  ScenarioButtons,
  WinProbabilityCurve,
  HistoricalComparison,
  CompetitorDistribution,
  AdvancedSettings,
  SaveStrategyModal,
} from '@widgets/index'
import type { PricingStrategy } from '@widgets/pricing/SaveStrategyModal'
import { useTenderDetail } from '@hooks/tender'
import { useSavePricingStrategy } from '@hooks/pricing'
import { usePricingScenarios } from '@hooks/index'

const FALLBACK_SCENARIOS = [
  { label: 'Conservative', discount: -2, type: 'conservative' as const, description: 'Safe bid, higher win prob' },
  { label: 'Competitive', discount: -8, type: 'competitive' as const, description: 'Balanced risk/reward' },
  { label: 'Aggressive', discount: -15, type: 'aggressive' as const, description: 'Bold bid, low win prob' },
]

export function PricingLaboratory() {
  const { id: tenderId } = useParams<{ id: string }>()
  const [discount, setDiscount] = useState(-12)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showSaveModal, setShowSaveModal] = useState(false)

  const { data: tenderDetail } = useTenderDetail(tenderId ?? '')
  const { data: scenariosData } = usePricingScenarios()

  const sorBaseline = useMemo(() => {
    const raw = tenderDetail?.variables?.estimated_cost_bdt ?? tenderDetail?.variables?.estimated_cost
    return raw ? Number(raw) : 45.2e7
  }, [tenderDetail])

  const cost = sorBaseline * 0.843

  const bidPrice = sorBaseline * (1 + discount / 100)
  const marginIfWon = bidPrice - cost
  const marginPercent = (marginIfWon / bidPrice) * 100
  const winProbability = Math.max(10, Math.min(95, 50 + Math.abs(discount) * 3))
  const expectedValue = (marginIfWon * winProbability) / 100

  const saveStrategy = useSavePricingStrategy()

  const scenarioEntries = Object.values(scenariosData?.scenarios ?? {})
  const scenarios = (scenarioEntries.length >= 2 ? scenarioEntries.map(s => ({
    label: s.label,
    discount: -s.discount_pct,
    type: 'competitive' as const,
    description: '',
  })) : FALLBACK_SCENARIOS)

  const handleSaveStrategy = (strategy: PricingStrategy) => {
    if (!tenderId) return
    saveStrategy.mutate({
      tenderId,
      strategy: {
        name: strategy.name ?? `Strategy ${discount}%`,
        discount_percent: Math.abs(discount),
        bid_price: bidPrice,
        rationale: strategy.rationale ?? '',
      },
    })
  }

  const handleShareStrategy = () => {
    const url = `${window.location.href}?discount=${discount}`
    navigator.clipboard.writeText(url)
  }

  return (
    <>
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Pricing Laboratory</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">Explore pricing strategy: discount vs win probability vs profit</p>
        </div>
      }
      primary={
        <div className="space-y-6">
          {/* Main Controls */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <DiscountSlider
              value={discount}
              onChange={setDiscount}
              sorBaseline={sorBaseline}
              cost={cost}
            />

            {/* Center: Key Metrics */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Real-Time Metrics</h3>

              <div className="space-y-4">
                <div className="rounded-lg border-2 border-green-200 bg-green-50 p-3 dark:border-green-700 dark:bg-green-900/30">
                  <p className="text-xs font-medium text-green-600 dark:text-green-400">Win Probability</p>
                  <p className="text-2xl font-bold text-green-900 dark:text-green-300">{winProbability.toFixed(0)}%</p>
                </div>

                <ProfitMarginDisplay
                  marginPercent={marginPercent}
                  marginIfWon={marginIfWon}
                  bidPrice={bidPrice}
                  cost={cost}
                />

                <ExpectedValueCard
                  expectedValue={expectedValue}
                  marginIfWon={marginIfWon}
                  winProbability={winProbability}
                />
              </div>

              <button
                onClick={() => setShowAdvanced(true)}
                className="mt-4 w-full rounded-lg border border-gray-300 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                ⚙️ Advanced Settings
              </button>
            </div>

            <ScenarioButtons
              scenarios={scenarios}
              selectedDiscount={discount}
              onScenarioSelect={setDiscount}
              onSaveStrategy={() => setShowSaveModal(true)}
              onShareStrategy={handleShareStrategy}
            />
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <WinProbabilityCurve discount={discount} winProbability={winProbability} />
            <HistoricalComparison discount={discount} />
            <CompetitorDistribution bidPrice={bidPrice} sorBaseline={sorBaseline} />
          </div>
        </div>
      }
    />
      <AdvancedSettings isOpen={showAdvanced} onClose={() => setShowAdvanced(false)} />
      <SaveStrategyModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        onSave={handleSaveStrategy}
        discount={discount}
        expectedValue={expectedValue}
        winProbability={winProbability}
      />
    </>
  )
}
