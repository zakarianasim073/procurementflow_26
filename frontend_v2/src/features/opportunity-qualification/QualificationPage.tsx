import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, AlertTriangle, ChevronRight, Shield, Trophy, TrendingUp, Building2 } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { useTenderDetail } from '@hooks/index'
import { useContractorCapacity, useContractorFinance, useTenderRecommendation, useTenderTDSCriteria } from '@hooks/index'

type QualifyStep = 'qualify' | 'recommend' | 'probability'

const STEPS: Array<{ id: QualifyStep; label: string; description: string }> = [
  { id: 'qualify', label: 'Qualify', description: 'Check eligibility criteria' },
  { id: 'recommend', label: 'Recommendation', description: 'AI bid/no-bid decision' },
  { id: 'probability', label: 'Win Probability', description: 'Predicted success rate' },
]

function StepIndicator({ currentStep }: { currentStep: QualifyStep }) {
  const currentIdx = STEPS.findIndex((s) => s.id === currentStep)

  return (
    <nav aria-label="Qualification steps" className="mb-6">
      <ol className="flex items-center" role="list">
        {STEPS.map((step, idx) => (
          <li key={step.id} className="flex items-center" role="listitem">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold',
                  idx < currentIdx && 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
                  idx === currentIdx && 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
                  idx > currentIdx && 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                )}
                aria-current={idx === currentIdx ? 'step' : undefined}
              >
                {idx < currentIdx ? <CheckCircle className="h-4 w-4" /> : idx + 1}
              </span>
              <span className={cn(
                'text-sm font-medium',
                idx === currentIdx ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'
              )}>
                {step.label}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <ChevronRight className="mx-3 h-4 w-4 text-gray-300 dark:text-gray-600" />
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}

function QualifyStepContent({ tenderId, contractorId }: { tenderId: string; contractorId: string }) {
  const tds = useTenderTDSCriteria(tenderId)
  const capacity = useContractorCapacity(contractorId)

  if (tds.isLoading || capacity.isLoading) {
    return <div className="space-y-3"><Skeleton className="h-32 w-full rounded-xl" /><Skeleton className="h-32 w-full rounded-xl" /></div>
  }

  const criteria = tds.data

  return (
    <div className="space-y-4">
      {criteria && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <Shield size={14} /> TDS Financial Criteria
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {criteria.general_experience && (
              <CriteriaCard label="General Experience" value={criteria.general_experience} />
            )}
            {criteria.specific_experience_value != null && (
              <CriteriaCard label="Specific Experience (Value)" value={`Tk. ${(criteria.specific_experience_value / 1e5).toFixed(1)}L`} />
            )}
            {criteria.specific_experience_count != null && (
              <CriteriaCard label="Similar Works Required" value={`${criteria.specific_experience_count} projects`} />
            )}
            {criteria.avg_annual_turnover != null && (
              <CriteriaCard label="Avg Annual Turnover" value={`Tk. ${(criteria.avg_annual_turnover / 1e7).toFixed(1)}Cr`} />
            )}
            {criteria.liquid_assets != null && (
              <CriteriaCard label="Liquid Assets" value={`Tk. ${(criteria.liquid_assets / 1e7).toFixed(1)}Cr`} />
            )}
            {criteria.min_tender_capacity != null && (
              <CriteriaCard label="Min Tender Capacity" value={`Tk. ${(criteria.min_tender_capacity / 1e7).toFixed(1)}Cr`} />
            )}
            {criteria.tender_security != null && (
              <CriteriaCard label="Tender Security" value={`Tk. ${(criteria.tender_security / 1e5).toFixed(1)}L`} />
            )}
            {criteria.performance_security != null && (
              <CriteriaCard label="Performance Security" value={`${criteria.performance_security}%`} />
            )}
            {criteria.retention_money != null && (
              <CriteriaCard label="Retention Money" value={`${criteria.retention_money}%`} />
            )}
          </div>
        </div>
      )}

      {capacity.data && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <Building2 size={14} /> Capacity Assessment
          </h2>
          <div className="mb-3 flex items-center gap-2">
            <span className={cn(
              'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
              capacity.data.capacity_status === 'available' && 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
              capacity.data.capacity_status === 'tight' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
              capacity.data.capacity_status === 'overloaded' && 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
            )}>
              {capacity.data.capacity_status === 'available' && <CheckCircle className="mr-1 h-3 w-3" />}
              {capacity.data.capacity_status.charAt(0).toUpperCase() + capacity.data.capacity_status.slice(1)}
            </span>
            <span className="ml-auto text-xs text-gray-400">Confidence: {(capacity.data.data_confidence_score * 100).toFixed(0)}%</span>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Work in Hand" value={`Tk. ${(capacity.data.work_in_hand_bdt / 1e7).toFixed(1)}Cr`} />
            <StatCard label="Tender Capacity" value={`Tk. ${(capacity.data.tender_capacity_bdt / 1e7).toFixed(1)}Cr`} />
            <StatCard label="Utilization" value={`${(capacity.data.utilization_ratio * 100).toFixed(0)}%`} />
            <StatCard label="Turnover (Est.)" value={`Tk. ${(capacity.data.estimated_turnover_bdt / 1e7).toFixed(1)}Cr`} />
          </div>
          {capacity.data.agencies_worked.length > 0 && (
            <p className="mt-3 text-xs text-gray-400">Agencies worked: {capacity.data.agencies_worked.slice(0, 5).join(', ')}</p>
          )}
        </div>
      )}

      {!criteria && !capacity.data && (
        <EmptyState title="No qualification data" description="TDS criteria and capacity data are not available for this tender." />
      )}
    </div>
  )
}

function RecommendStepContent({ tenderId, contractorId }: { tenderId: string; contractorId: string }) {
  const rec = useTenderRecommendation(tenderId, contractorId)
  const finance = useContractorFinance(contractorId)

  if (rec.isLoading || finance.isLoading) {
    return <div className="space-y-3"><Skeleton className="h-48 w-full rounded-xl" /><Skeleton className="h-32 w-full rounded-xl" /></div>
  }

  const recommendation = rec.data

  if (!recommendation) {
    return <EmptyState title="No recommendation" description="Recommendation data is not available for this tender." />
  }

  const decisionColor = {
    BID: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
    CONSIDER: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
    RISKY_BID: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400',
    NO_BID: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  }[recommendation.recommendation]

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <Trophy size={14} /> AI Recommendation
          </h2>
          <span className={cn('inline-flex items-center rounded-full px-3 py-1 text-xs font-bold', decisionColor)}>
            {recommendation.recommendation.replace('_', ' ')}
          </span>
        </div>

        <div className="mb-4 grid grid-cols-3 gap-3">
          <StatCard label="Win Probability" value={`${recommendation.win_probability_estimate.toFixed(1)}%`} />
          <StatCard label="Confidence" value={`${recommendation.confidence_pct.toFixed(0)}%`} />
          <StatCard label="Score" value={`${recommendation.recommendation_score.toFixed(0)}/100`} />
        </div>

        {recommendation.recommended_bid_amount > 0 && (
          <p className="mb-3 text-sm text-gray-600 dark:text-gray-400">
            Recommended bid amount: <span className="font-semibold text-gray-900 dark:text-white">Tk. {(recommendation.recommended_bid_amount / 1e7).toFixed(2)}Cr</span>
          </p>
        )}

        {recommendation.explanation && (
          <p className="mb-3 text-sm text-gray-600 dark:text-gray-400">{recommendation.explanation}</p>
        )}

        {recommendation.risk_factors.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-semibold text-red-600 dark:text-red-400 flex items-center gap-1">
              <AlertTriangle size={12} /> Risk Factors
            </h3>
            <ul className="space-y-1">
              {recommendation.risk_factors.map((rf, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-red-600 dark:text-red-400">
                  <span className="mt-1 block h-1.5 w-1.5 shrink-0 rounded-full bg-red-500" />
                  {rf}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {finance.data && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <TrendingUp size={14} /> Financial Profile
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Health Score" value={`${(finance.data.health_score * 100).toFixed(0)}%`} />
            <StatCard label="Win Rate" value={`${(finance.data.win_rate * 100).toFixed(0)}%`} />
            <StatCard label="Completion Rate" value={`${(finance.data.completion_rate * 100).toFixed(0)}%`} />
            <StatCard label="Avg Discount" value={`${(finance.data.avg_discount_pct * 100).toFixed(1)}%`} />
          </div>
        </div>
      )}
    </div>
  )
}

function ProbabilityStepContent({ tenderId, contractorId }: { tenderId: string; contractorId: string }) {
  const rec = useTenderRecommendation(tenderId, contractorId)
  const finance = useContractorFinance(contractorId)

  if (rec.isLoading || finance.isLoading) {
    return <div className="space-y-3"><Skeleton className="h-40 w-full rounded-xl" /><Skeleton className="h-32 w-full rounded-xl" /></div>
  }

  const recommendation = rec.data

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Win Probability Analysis</h2>
        {recommendation ? (
          <div className="space-y-4">
            <div>
              <div className="mb-1 flex items-center justify-between text-xs text-gray-500">
                <span>Win Probability</span>
                <span className="font-semibold text-gray-900 dark:text-white">{recommendation.win_probability_estimate.toFixed(1)}%</span>
              </div>
              <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    recommendation.win_probability_estimate >= 60 && 'bg-green-500',
                    recommendation.win_probability_estimate >= 35 && recommendation.win_probability_estimate < 60 && 'bg-yellow-500',
                    recommendation.win_probability_estimate < 35 && 'bg-red-500',
                  )}
                  style={{ width: `${Math.min(recommendation.win_probability_estimate, 100)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between text-xs text-gray-500">
                <span>Confidence Level</span>
                <span className="font-semibold text-gray-900 dark:text-white">{recommendation.confidence_pct.toFixed(0)}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                <div
                  className="h-full rounded-full bg-blue-500 transition-all"
                  style={{ width: `${Math.min(recommendation.confidence_pct, 100)}%` }}
                />
              </div>
            </div>

            {recommendation.factors && Object.keys(recommendation.factors).length > 0 && (
              <div>
                <h3 className="mb-2 text-xs font-semibold text-gray-600 dark:text-gray-400">Factor Breakdown</h3>
                <div className="space-y-1.5">
                  {Object.entries(recommendation.factors).map(([factor, score]) => (
                    <div key={factor} className="flex items-center gap-2">
                      <span className="w-32 text-xs text-gray-500 dark:text-gray-400 capitalize">{factor.replace(/_/g, ' ')}</span>
                      <div className="flex-1 h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                        <div
                          className={cn(
                            'h-full rounded-full',
                            score >= 0.6 && 'bg-green-500',
                            score >= 0.35 && score < 0.6 && 'bg-yellow-500',
                            score < 0.35 && 'bg-red-500',
                          )}
                          style={{ width: `${Math.min(score * 100, 100)}%` }}
                        />
                      </div>
                      <span className="w-10 text-right text-xs tabular-nums text-gray-500">{(score * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState title="No probability data" description="Win probability data is not available for this tender." />
        )}
      </div>

      {finance.data && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Historical Performance</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatCard label="Total Bids" value={String(finance.data.total_bids)} />
            <StatCard label="Avg Delay" value={`${finance.data.avg_delay_days.toFixed(1)} days`} />
            <StatCard label="Reliability" value={`${(finance.data.reliability_score * 100).toFixed(0)}%`} />
          </div>
        </div>
      )}
    </div>
  )
}

function CriteriaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-0.5 text-sm font-bold tabular-nums text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

export function QualificationPage() {
  const { id } = useParams<{ id: string }>()
  const [step, setStep] = useState<QualifyStep>('qualify')
  const [contractorId, setContractorId] = useState(
    () => localStorage.getItem('procureflow-shortlist-contractor') ?? '',
  )
  const detail = useTenderDetail(id ?? '')

  const currentIdx = STEPS.findIndex((s) => s.id === step)
  const variables = detail.data?.variables ?? {} as Record<string, unknown>

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <Link to="/opportunity/discovery" className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300" aria-label="Back">
            <ArrowLeft size={18} />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
              {id ? `Qualify — ${id}` : 'Bid Qualification'}
            </h1>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
              {id ? (variables.title as string) || `Tender ${id}` : 'Select a tender to begin'}
            </p>
          </div>
        </div>
      }
      primary={
        id ? (
          <div>
            <div className="mb-4 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
              <label htmlFor="qualification-contractor" className="text-xs font-medium text-gray-600 dark:text-gray-400">
                Contractor ID or exact company name
              </label>
              <div className="mt-1 flex gap-2">
                <input
                  id="qualification-contractor"
                  value={contractorId}
                  onChange={event => setContractorId(event.target.value)}
                  onBlur={() => localStorage.setItem('procureflow-shortlist-contractor', contractorId.trim())}
                  placeholder="Select the contractor being qualified"
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
                />
              </div>
            </div>
            <StepIndicator currentStep={step} />
            <div className="mb-4 flex gap-2">
              {STEPS.map((s, i) => (
                <button
                  key={s.id}
                  onClick={() => setStep(s.id)}
                  disabled={i > currentIdx + 1}
                  className={cn(
                    'flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors',
                    step === s.id ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400' : 'bg-gray-50 text-gray-500 hover:bg-gray-100 dark:bg-gray-800/60 dark:text-gray-400 dark:hover:bg-gray-800',
                    i > currentIdx + 1 && 'cursor-not-allowed opacity-40'
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>

            {step === 'qualify' && <QualifyStepContent tenderId={id} contractorId={contractorId.trim()} />}
            {step === 'recommend' && <RecommendStepContent tenderId={id} contractorId={contractorId.trim()} />}
            {step === 'probability' && <ProbabilityStepContent tenderId={id} contractorId={contractorId.trim()} />}

            <div className="mt-4 flex justify-between">
              <button
                onClick={() => { const idx = STEPS.findIndex(s => s.id === step) - 1; if (idx >= 0) setStep(STEPS[idx].id) }}
                disabled={currentIdx === 0}
                className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-30 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Previous
              </button>
              <button
                onClick={() => { const idx = STEPS.findIndex(s => s.id === step) + 1; if (idx < STEPS.length) setStep(STEPS[idx].id) }}
                disabled={currentIdx === STEPS.length - 1}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-30"
              >
                Next
              </button>
            </div>
          </div>
        ) : (
          <EmptyState title="No tender selected" description="Navigate from Discovery to select a tender for qualification." />
        )
      }
    />
  )
}
