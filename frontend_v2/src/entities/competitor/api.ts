import { fetchJson } from '@entities/sharedApi'
import type { Competitor, CompetitorAnalysis } from './types'

const V1 = '/api'

export function getCompetitors(params?: { district?: string; category?: string; search?: string; skip?: number; limit?: number }): Promise<Competitor[]> {
  const qs = new URLSearchParams()
  if (params?.district) qs.set('district', params.district)
  if (params?.category) qs.set('category', params.category)
  if (params?.search) qs.set('search', params.search)
  if (params?.skip) qs.set('skip', String(params.skip))
  if (params?.limit) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return fetchJson<Array<Record<string, any>>>(`${V1}/competitors/${query ? `?${query}` : ''}`)
    .then((rows) => rows.map((row) => {
      const specializations = row.specializations ?? {}
      const agencies = row.agencies
        ?? (row.category ? [row.category] : [])
      return {
        competitor_id: String(row.competitor_id ?? row.id),
        name: String(row.name ?? 'Unknown contractor'),
        win_rate: Number(row.win_rate ?? specializations.win_rate ?? row.predicted_win_probability ?? 0),
        total_bids: Number(row.total_bids ?? row.total_awards ?? 0),
        total_wins: Number(row.total_wins ?? row.total_awards ?? 0),
        avg_discount: Number(row.avg_discount ?? row.avg_discount_pct ?? 0),
        specialties: Array.isArray(row.specialties)
          ? row.specialties
          : Object.keys(row.work_types ?? {}),
        agencies: Array.isArray(agencies) ? agencies : Object.keys(agencies ?? {}),
        recent_activity: Array.isArray(row.recent_activity) ? row.recent_activity : [],
      }
    }))
}

export function getCompetitorStats(): Promise<{
  total_competitors: number
  total_awarded_amount: number
  source: string
  by_category: Array<{ category: string; count: number }>
  by_district: Array<{ district: string; count: number }>
}> {
  return fetchJson(`${V1}/competitors/stats`)
}

export function getCompetitorDetail(competitorId: string): Promise<Competitor> {
  return fetchJson<Competitor>(`${V1}/competitors/${competitorId}`)
}

export function getCompetitorAwards(competitorId: string): Promise<Array<Record<string, unknown>>> {
  return fetchJson(`${V1}/competitors/${competitorId}/awards`)
}

export function getCompetitorAnalysis(tenderId: string): Promise<CompetitorAnalysis | null> {
  return fetchJson<CompetitorAnalysis | null>(`${V1}/competitors/analysis/${tenderId}`)
}
