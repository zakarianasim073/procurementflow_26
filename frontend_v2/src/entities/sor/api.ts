import { fetchJson } from '@entities/sharedApi'
import type { SorSearchResult, SorAgency, SorComparison } from './types'

const V1 = '/api'

export function searchSor(query: string, agency?: string): Promise<SorSearchResult> {
  const qs = new URLSearchParams({ q: query })
  if (agency) qs.set('agency', agency)
  return fetchJson<SorSearchResult>(`${V1}/sor/lookup?${qs.toString()}`)
}

export function getSorAgencies(): Promise<{ agencies: SorAgency[] }> {
  return fetchJson<{ agencies: SorAgency[] }>(`${V1}/sor/agencies`)
}

export function lookupSorRate(code: string, agency?: string, zone?: string, description?: string): Promise<{
  code: string
  description: string
  unit: string
  zone_a: number
  zone_b: number
  zone_c: number
  zone_d: number
  rate: number
  zone: string
  agency: string
}> {
  const qs = new URLSearchParams({ code })
  if (agency) qs.set('agency', agency)
  if (zone) qs.set('zone', zone)
  if (description) qs.set('description', description)
  return fetchJson(`${V1}/sor/lookup?${qs.toString()}`)
}

export function compareSor(codes: string[], agencies: string[]): Promise<SorComparison[]> {
  return fetchJson<SorComparison[]>(`${V1}/sor/compare`, {
    method: 'POST',
    body: JSON.stringify({ codes, agencies }),
  })
}
