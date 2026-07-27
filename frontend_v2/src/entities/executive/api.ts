import type { ExecutiveOverview, ExecutivePipeline, LiveMetrics, MarketOverview, ExecutiveReport, PredictionsModelStatus, AgencyLiveTenderResponse, LiveEnrichmentQueueResponse, BidShortlistResponse } from './types'
import { fetchJson } from '../sharedApi'

const BASE = '/api'

// ── V1 Endpoints ───────────────────────────────────────────────────

export function getExecutiveOverview(): Promise<ExecutiveOverview> {
  return fetchJson<ExecutiveOverview>(`${BASE}/executive/overview`)
}

export function getExecutivePipeline(): Promise<ExecutivePipeline> {
  return fetchJson<ExecutivePipeline>(`${BASE}/executive/pipeline`)
}

export function getAgencyLiveTenders(agencyCode: string): Promise<AgencyLiveTenderResponse> {
  return fetchJson<AgencyLiveTenderResponse>(
    `${BASE}/executive/pipeline/${encodeURIComponent(agencyCode)}/tenders?limit=500`,
  )
}

export function getLiveEnrichmentQueue(): Promise<LiveEnrichmentQueueResponse> {
  return fetchJson<LiveEnrichmentQueueResponse>(`${BASE}/executive/enrichment-queue?limit=100`)
}

export function refreshLiveEnrichmentQueue(limit = 20, minValueBdt = 10_000_000) {
  return fetchJson<{ success: boolean; created: number; skipped: number }>(
    `${BASE}/executive/enrichment-queue/refresh?limit=${limit}&min_value_bdt=${minValueBdt}`,
    { method: 'POST' },
  )
}

export function runLiveEnrichmentQueue(limit = 3) {
  return fetchJson<{ success: boolean; started: number; entry_ids: string[] }>(
    `${BASE}/executive/enrichment-queue/run?limit=${limit}&retry_failed=true`,
    { method: 'POST' },
  )
}

export function getBidShortlist(contractor?: string): Promise<BidShortlistResponse> {
  const query = contractor ? `?contractor=${encodeURIComponent(contractor)}` : ''
  return fetchJson<BidShortlistResponse>(`${BASE}/executive/bid-shortlist${query}`)
}

export interface TenderAlertFilter {
  id: string
  name: string
  agencies: string[]
  districts: string[]
  min_value_bdt: number
  max_value_bdt: number | null
  work_types: string[]
  eligibility_keywords: string[]
  deadline_days: number
  active: boolean
  last_evaluated_at: string | null
  last_match_count: number
}

export interface TenderAlertNotification {
  id: string
  tender_id: string
  filter_id: string
  filter_name: string
  title: string
  package_no: string | null
  agency_code: string
  district: string | null
  estimated_cost_bdt: number
  closing_datetime: string | null
  matched_at: string
  read: boolean
}

export interface TenderAlertsResponse {
  success: boolean
  filters: TenderAlertFilter[]
  notifications: TenderAlertNotification[]
  unread: number
}

export function getTenderAlerts(): Promise<TenderAlertsResponse> {
  return fetchJson<TenderAlertsResponse>(`${BASE}/executive/tender-alerts`)
}

export function createTenderAlertFilter(input: Omit<TenderAlertFilter, 'id' | 'last_evaluated_at' | 'last_match_count'>) {
  return fetchJson<{ success: boolean; filter: TenderAlertFilter; matches: number; notifications_created: number }>(
    `${BASE}/executive/tender-alerts/filters`,
    { method: 'POST', body: JSON.stringify(input) },
  )
}

export function deleteTenderAlertFilter(filterId: string) {
  return fetchJson<{ success: boolean }>(
    `${BASE}/executive/tender-alerts/filters/${encodeURIComponent(filterId)}`,
    { method: 'DELETE' },
  )
}

export function evaluateTenderAlerts() {
  return fetchJson<{ success: boolean; matches: number; notifications_created: number }>(
    `${BASE}/executive/tender-alerts/evaluate`,
    { method: 'POST' },
  )
}

export function markTenderAlertRead(notificationId: string) {
  return fetchJson<{ success: boolean }>(
    `${BASE}/executive/tender-alerts/notifications/${encodeURIComponent(notificationId)}/read`,
    { method: 'POST' },
  )
}

export function getExecutiveReport(): Promise<ExecutiveReport> {
  return fetchJson<ExecutiveReport>(`${BASE}/executive/report`)
}

// ── V2 Endpoints ───────────────────────────────────────────────────

export function getMarketOverview(): Promise<MarketOverview> {
  return fetchJson<MarketOverview>(`${BASE}/v2/analytics/market-overview`, true)
}

export function getLiveMetrics(): Promise<LiveMetrics> {
  return fetchJson<LiveMetrics>(`${BASE}/v2/analytics/live-metrics`, true)
}

export function getPredictionsModelStatus(): Promise<PredictionsModelStatus> {
  return fetchJson<PredictionsModelStatus>(`${BASE}/v2/predictions/models/status`, true)
}
