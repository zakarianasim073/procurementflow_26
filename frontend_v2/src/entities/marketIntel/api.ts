import { fetchJson } from '../sharedApi'
import type {
  MarketOverviewStats,
  AwardHistoryYear,
  AgencyBehaviour,
  ContractorStanding,
  NppiAnalysis,
} from './types'

const BASE = '/api/v2/market-intelligence'

/** Headline market figures across procurement_lifecycle. */
export function getMarketOverview(): Promise<MarketOverviewStats> {
  return fetchJson<MarketOverviewStats>(`${BASE}/overview`, true)
}

/** Awards per year, newest first. */
export function getAwardHistory(years = 8, agency?: string): Promise<AwardHistoryYear[]> {
  const qs = new URLSearchParams({ years: String(years) })
  if (agency) qs.set('agency', agency)
  return fetchJson<AwardHistoryYear[]>(`${BASE}/award-history?${qs}`, true)
}

/** Per-agency awarding behaviour, busiest first. */
export function getAgencyBehaviour(limit = 15): Promise<AgencyBehaviour[]> {
  return fetchJson<AgencyBehaviour[]>(`${BASE}/agencies?limit=${limit}`, true)
}

/** Most active winning contractors. */
export function getTopContractors(limit = 20, agency?: string): Promise<ContractorStanding[]> {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (agency) qs.set('agency', agency)
  return fetchJson<ContractorStanding[]>(`${BASE}/contractors?${qs}`, true)
}

/** NPPI distribution overall and by agency. */
export function getNppiAnalysis(): Promise<NppiAnalysis> {
  return fetchJson<NppiAnalysis>(`${BASE}/nppi`, true)
}
