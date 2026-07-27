import { fetchJson, type FetchJsonOptions } from '../sharedApi'
import type { MonitorStats, MonitorAlertsResponse, WatchdogHealth, WatchdogError, SystemMetrics, EndpointHealth, WatchdogAlert, ErrorTrend, HealthScore } from './types'

const BASE_V2 = '/api/v2/monitoring'

export function getMonitorStats(): Promise<MonitorStats> {
  return fetchJson<MonitorStats>(`${BASE_V2}/stats`, true)
}

export function getMonitorAlerts(limit = 50): Promise<MonitorAlertsResponse> {
  return fetchJson<MonitorAlertsResponse>(`${BASE_V2}/alerts?limit=${limit}`, true)
}

export function getWatchdogHealth(): Promise<WatchdogHealth> {
  return fetchJson<WatchdogHealth>(`${BASE_V2}/watchdog/health`, true)
}

export function getWatchdogErrors(limit = 20): Promise<WatchdogError[]> {
  return fetchJson<WatchdogError[]>(`${BASE_V2}/watchdog/errors?limit=${limit}`, true)
}

// v2.1 Enhanced endpoints
export function getSystemMetrics(): Promise<SystemMetrics> {
  return fetchJson<SystemMetrics>(`${BASE_V2}/watchdog/metrics`, true)
}

export function getMetricsHistory(limit = 100): Promise<SystemMetrics[]> {
  return fetchJson<SystemMetrics[]>(`${BASE_V2}/watchdog/metrics/history?limit=${limit}`, true)
}

export function checkApiEndpoints(): Promise<Record<string, EndpointHealth>> {
  return fetchJson<Record<string, EndpointHealth>>(`${BASE_V2}/watchdog/endpoints/check`, { method: 'POST', authed: true })
}

export function getEndpointHealth(): Promise<Record<string, EndpointHealth>> {
  return fetchJson<Record<string, EndpointHealth>>(`${BASE_V2}/watchdog/endpoints`, true)
}

export function getWatchdogAlerts(limit = 50, resolved = false): Promise<WatchdogAlert[]> {
  return fetchJson<WatchdogAlert[]>(`${BASE_V2}/watchdog/alerts?limit=${limit}&resolved=${resolved}`, true)
}

export function acknowledgeAlert(alertId: string): Promise<{ success: boolean }> {
  return fetchJson<{ success: boolean }>(`${BASE_V2}/watchdog/alerts/${alertId}/acknowledge`, { method: 'POST', authed: true })
}

export function resolveAlert(alertId: string, resolution?: string): Promise<{ success: boolean }> {
  return fetchJson<{ success: boolean }>(`${BASE_V2}/watchdog/alerts/${alertId}/resolve`, { method: 'POST', body: JSON.stringify({ resolution }), authed: true })
}

export function getErrorTrends(hours = 24, source?: string, errorType?: string): Promise<ErrorTrend[]> {
  const params = new URLSearchParams({ hours: hours.toString() })
  if (source) params.append('source', source)
  if (errorType) params.append('error_type', errorType)
  return fetchJson<ErrorTrend[]>(`${BASE_V2}/watchdog/errors/trends?${params}`, true)
}

export function getHealthScore(): Promise<HealthScore> {
  return fetchJson<HealthScore>(`${BASE_V2}/watchdog/health/score`, true)
}
