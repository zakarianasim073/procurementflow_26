import { fetchJson } from '@entities/sharedApi'
import type { AgentResultsResponse, AgenciesResponse, CrawlerStatusResponse, OpeningReportsResponse } from './types'

const BASE = '/api/v2/opportunity'

export function getTenderRadar(): Promise<Record<string, unknown>> {
  return fetchJson(`${BASE}/radar`, true)
}

export async function getRecentAgentResults(limit = 10): Promise<AgentResultsResponse> {
  const data = await fetchJson<Omit<AgentResultsResponse, 'success'>>(
    `/api/agent-results/recent?limit=${limit}`,
    true,
  )
  return { success: true, ...data }
}

export function getAgencies(): Promise<AgenciesResponse> {
  return fetchJson<AgenciesResponse>(`${BASE}/agencies`, true)
}

export function getCrawlerStatus(): Promise<CrawlerStatusResponse> {
  return fetchJson<CrawlerStatusResponse>(`${BASE}/crawler/status`, true)
}

export function getOpeningReports(limit = 10): Promise<OpeningReportsResponse> {
  return fetchJson<OpeningReportsResponse>(`${BASE}/opening-reports?limit=${limit}`, true)
}
