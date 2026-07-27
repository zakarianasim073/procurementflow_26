import { fetchJson } from '@entities/sharedApi'
import type { Award, AwardStats } from './types'

const V1 = '/api'

export function getAwards(params?: { procuring_entity?: string; contractor_name?: string; district?: string; work_type?: string; date_from?: string; date_to?: string; skip?: number; limit?: number }): Promise<Award[]> {
  const qs = new URLSearchParams()
  if (params?.procuring_entity) qs.set('procuring_entity', params.procuring_entity)
  if (params?.contractor_name) qs.set('contractor_name', params.contractor_name)
  if (params?.district) qs.set('district', params.district)
  if (params?.work_type) qs.set('work_type', params.work_type)
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  if (params?.skip) qs.set('skip', String(params.skip))
  if (params?.limit) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return fetchJson<Award[]>(`${V1}/awards${query ? `?${query}` : ''}`)
}

export function getAwardStats(): Promise<AwardStats> {
  return fetchJson<AwardStats>(`${V1}/awards/stats`)
}

export function getAwardDetail(awardId: string): Promise<Award> {
  return fetchJson<Award>(`${V1}/awards/${awardId}`)
}
