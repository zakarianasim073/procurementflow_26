import type { PartnerValueMetrics, ExecutiveRoiReport } from './types'
import { fetchJson } from '@entities/sharedApi'
import { getAuthToken } from '@entities/authToken'
import { authReady } from '@entities/bootstrapAuth'

const BASE = '/api/v2/executive/roi'

interface BackendRoiMetrics {
  hours_saved: number
  hours_saved_breakdown: Record<string, number>
  compliance_issues_detected: number
  compliance_issues_prevented: number
  win_rate_before: number
  win_rate_after: number
  win_rate_improvement: number
  value_created: number
  pricing_accuracy: number
}

interface BackendPartnerMetrics {
  partner_name: string
  hours_saved: number
  features_adopted: number
  top_tenders: Array<Record<string, unknown>>
  adoption_days: number
  adoption_timeline: Array<{ date?: string; event?: string; usage?: number }>
}

export async function getExecutiveRoi(params?: { period?: string; start?: string; end?: string }): Promise<ExecutiveRoiReport> {
  const qs = new URLSearchParams()
  if (params?.period) qs.set('period', params.period)
  if (params?.start) qs.set('start', params.start)
  if (params?.end) qs.set('end', params.end)
  const query = qs.toString()
  const metrics = await fetchJson<BackendRoiMetrics>(query ? `${BASE}?${query}` : BASE, true)
  const period = (params?.period === 'quarter' || params?.period === 'year') ? params.period : 'month'

  return {
    period,
    date_range: { start: params?.start ?? '', end: params?.end ?? '' },
    aggregate: {
      total_partners: 0,
      total_hours_saved: metrics.hours_saved,
      total_contracts_analyzed: 0,
      total_win_rate_improvement: metrics.win_rate_improvement,
      compliance_issues_prevented: metrics.compliance_issues_prevented,
      estimated_value_created: metrics.value_created,
    },
    partner_rankings: [],
    adoption_momentum: 'steady',
    feature_adoption: {
      pricing_panel_usage: metrics.pricing_accuracy,
      competitor_intel_usage: 0,
      compliance_check_usage: metrics.compliance_issues_detected,
    },
  }
}

export async function getPartnerMetrics(companyId: string): Promise<PartnerValueMetrics> {
  const metrics = await fetchJson<BackendPartnerMetrics>(`${BASE}/${companyId}`, true)
  const adoptionCurve = metrics.adoption_timeline.map((item, index) => ({
    week: item.date ?? `W${index + 1}`,
    active_users: item.usage ?? 0,
  }))

  return {
    company_id: companyId,
    company_name: metrics.partner_name,
    active_users: adoptionCurve.at(-1)?.active_users ?? 0,
    tenders_analyzed: metrics.top_tenders.length,
    bids_placed_with_pf: metrics.top_tenders.length,
    hours_saved: {
      total: metrics.hours_saved,
      per_tender: metrics.hours_saved / Math.max(metrics.top_tenders.length, 1),
      breakdown: { research: 0, bid_prep: 0, compliance_check: 0 },
    },
    compliance_improvements: {
      tenders_analyzed_for_compliance: 0,
      issues_detected_by_pf: 0,
      issues_avoided: 0,
      compliance_score_pre: 0,
      compliance_score_post: 0,
    },
    win_rate: {
      post_adoption: 0,
      tenders_won_with_pf: 0,
      tenders_lost_with_pf: 0,
    },
    pricing_accuracy: {
      ai_price_matches: 0,
      ai_price_avg_delta_percent: 0,
      user_followed_ai_price: 0,
    },
    user_adoption_curve: adoptionCurve,
    edf_feedback_rate: 0,
    edf_helpfulness_score: 0,
  }
}

export async function exportRoiPdf(params?: { period?: string }): Promise<Blob> {
  const qs = new URLSearchParams()
  if (params?.period) qs.set('period', params.period)
  await authReady()
  const token = getAuthToken()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}/export?${qs.toString()}`, { headers })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.blob()
}
