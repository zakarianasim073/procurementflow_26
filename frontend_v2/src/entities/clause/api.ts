import type { Clause, ClauseListResult } from './types'

const BASE = '/api/v2/clauses'

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}

export function getClauses(params?: { schedule?: string; page?: number; page_size?: number }): Promise<ClauseListResult> {
  const qs = new URLSearchParams()
  if (params?.schedule) qs.set('schedule', params.schedule)
  if (params?.page != null) qs.set('page', String(params.page))
  if (params?.page_size != null) qs.set('page_size', String(params.page_size))
  const query = qs.toString()
  return fetchJson<ClauseListResult>(query ? `${BASE}?${query}` : BASE)
}

export function getClause(clauseId: string): Promise<Clause> {
  return fetchJson<Clause>(`${BASE}/${clauseId}`)
}

export function searchClauses(q: string): Promise<ClauseListResult> {
  return fetchJson<ClauseListResult>(`${BASE}/search?q=${encodeURIComponent(q)}`)
}

export function getRelatedClauses(clauseId: string): Promise<Clause[]> {
  return fetchJson<Clause[]>(`${BASE}/${clauseId}/related`)
}
