import { useParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import {
  ContractorHeader, ExecutiveSummary, ExperienceGraph, EligibilityTracker,
  AwardHistory, WinRateTrend, PeerComparison, RiskProfile, OpportunityScout,
} from '@widgets/contractor'
import { useContractorProfile, useExperience, useRiskProfile, useOpportunities, usePprRules, useWinRate } from '@hooks/index'
import { useAwards } from '@hooks/contractor'

export function CompanyBrainPage() {
  const { companyId } = useParams<{ companyId: string }>()
  const profileQ = useContractorProfile(companyId)
  const expQ = useExperience(companyId)
  const awardsQ = useAwards(companyId)
  const riskQ = useRiskProfile(companyId)
  const oppsQ = useOpportunities(companyId)
  const pprQ = usePprRules('eligibility')
  const winRateQ = useWinRate(companyId)

  const isLoading = profileQ.isLoading || expQ.isLoading || awardsQ.isLoading || riskQ.isLoading || oppsQ.isLoading || pprQ.isLoading || winRateQ.isLoading

  const profile = profileQ.data
  const experience = expQ.data
  const awards = awardsQ.data
  const risk = riskQ.data
  const opportunities = oppsQ.data

  if (isLoading) {
    return (
      <ScreenTemplate
        header={<div><h1 className="text-2xl font-bold text-gray-900 dark:text-white">Company Brain</h1></div>}
        primary={<div className="flex items-center justify-center py-20"><Loader2 size={32} className="animate-spin text-gray-400" /></div>}
      />
    )
  }

  if (!profile) {
    return (
      <ScreenTemplate
        header={<div><h1 className="text-2xl font-bold text-gray-900 dark:text-white">Company Brain</h1></div>}
        primary={<div className="py-20 text-center text-sm text-gray-500">Contractor not found. Select a company to view its brain data.</div>}
      />
    )
  }

  const awardsList = (Array.isArray(awards) ? awards : awards?.awards ?? []).map((a) => ({
    awardDate: a.award_date, tender: a.tender_id,
    agency: '', category: a.category,
    value: a.contract_value, status: a.status,
  }))

  const riskDimensions = risk
    ? [
        { name: 'Compliance', level: (risk as any).compliance_risk ?? 'low', description: (risk as any).flags?.[0]?.flag ?? 'No issues' },
        { name: 'Market', level: (risk as any).market_risk ?? 'medium', description: '' },
        { name: 'Financial', level: (risk as any).financial_risk ?? 'low', description: '' },
        { name: 'Operational', level: (risk as any).operational_risk ?? 'low', description: '' },
      ]
    : profile.risk_profile
      ? [
          { name: 'Compliance', level: profile.risk_profile.compliance_risk ?? 'low', description: profile.risk_profile.flags?.[0]?.flag ?? '' },
          { name: 'Market', level: profile.risk_profile.market_risk ?? 'medium', description: '' },
          { name: 'Financial', level: profile.risk_profile.financial_risk ?? 'low', description: '' },
          { name: 'Operational', level: profile.risk_profile.operational_risk ?? 'low', description: '' },
        ]
      : []

  const oppsList = (opportunities as any[] | undefined) ?? profile.next_opportunities ?? []
  const mappedOpps = oppsList.map((o: any) => ({
    tender_id: o.tender_id, tender_name: o.tender_name ?? o.tender_id,
    agency: o.agency ?? '', category: o.category ?? '',
    value: o.value ?? o.contract_value ?? 0,
    match_score: o.match_score, reason: o.reason ?? '',
    partner_recommendation: o.partner_recommendation,
  }))

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Company Brain</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">Your contractor profile: eligibility, experience, awards, and opportunities</p>
        </div>
      }
      primary={
        <div className="space-y-6">
          <ContractorHeader
            name={profile.name}
            registrationId={profile.registration_id}
            status={profile.status}
            yearsOperating={profile.years_operating}
            ppr2025Eligible={profile.ppr2025_eligible}
            activeInEgpLast30d={profile.active_in_egp_last_30d}
          />
          <ExecutiveSummary text={profile.executive_summary ?? ''} highlights={experience?.by_category?.map((c: any) => `${c.projects_count} projects in ${c.category}`) ?? []} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ExperienceGraph />
            <EligibilityTracker
              rule37={pprQ.data?.[0] ? { rule: pprQ.data[0].title ?? pprQ.data[0].rule_id ?? 'Rule 37', status: 'met', detail: pprQ.data[0].description ?? '' } : undefined}
              rule38={pprQ.data?.[1] ? { rule: pprQ.data[1].title ?? pprQ.data[1].rule_id ?? 'Rule 38', status: 'met', detail: pprQ.data[1].description ?? '' } : undefined}
              rule40={pprQ.data?.[2] ? { rule: pprQ.data[2].title ?? pprQ.data[2].rule_id ?? 'Rule 40', status: 'met', detail: pprQ.data[2].description ?? '' } : undefined}
              gaps={profile.eligibility?.missing_categories ?? []}
            />
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <AwardHistory awards={awardsList} />
            <WinRateTrend />
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <PeerComparison
              you={{ name: profile.name, winRate: winRateQ.data?.[0]?.win_rate_pct ?? 0, priceDelta: 0 }}
              peers={[
                { name: 'XYZ Corp', winRate: 32, priceDelta: 5.1, ranking: 'below' },
                { name: 'DEF Ltd', winRate: 45, priceDelta: 2.1, ranking: 'above' },
              ]}
            />
            <RiskProfile
              dimensions={riskDimensions}
              overallRisk={risk?.overall_risk ?? profile.risk_profile?.overall_risk ?? 'low'}
              flags={risk?.flags?.map((f: any) => ({ severity: f.severity, text: f.flag, recommendation: f.recommendation })) ?? []}
            />
          </div>
          <OpportunityScout opportunities={mappedOpps} />
        </div>
      }
    />
  )
}
