import { useQuery } from '@tanstack/react-query'
import { getMonitorStats, getMonitorAlerts, getWatchdogHealth, getWatchdogErrors, getSystemMetrics, getMetricsHistory, checkApiEndpoints, getEndpointHealth, getWatchdogAlerts, acknowledgeAlert, resolveAlert, getErrorTrends, getHealthScore } from '@entities/monitoring'
import { fetchJson } from '@entities/sharedApi'
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function useMonitorStats() {
  return useQuery({
    queryKey: ['monitoring', 'stats'],
    queryFn: () => getMonitorStats(),
    staleTime: 30_000,
  })
}
export function useMonitorAlerts(limit = 50) {
  return useQuery({
    queryKey: ['monitoring', 'alerts', limit],
    queryFn: () => getMonitorAlerts(limit),
    staleTime: 30_000,
  })
}

export function useWatchdogHealth() {
  return useQuery({
    queryKey: ['monitoring', 'watchdog-health'],
    queryFn: () => getWatchdogHealth(),
    staleTime: 30_000,
  })
}

export function useWatchdogErrors(limit = 20) {
  return useQuery({
    queryKey: ['monitoring', 'watchdog-errors', limit],
    queryFn: () => getWatchdogErrors(limit),
    staleTime: 30_000,
  })
}

// v2.1 Enhanced hooks
export function useSystemMetrics() {
  return useQuery({
    queryKey: ['monitoring', 'system-metrics'],
    queryFn: () => getSystemMetrics(),
    staleTime: 10_000,
    refetchInterval: 30_000,
  })
}

export function useMetricsHistory(limit = 100) {
  return useQuery({
    queryKey: ['monitoring', 'metrics-history', limit],
    queryFn: () => getMetricsHistory(limit),
    staleTime: 30_000,
  })
}

export function useEndpointHealth() {
  return useQuery({
    queryKey: ['monitoring', 'endpoint-health'],
    queryFn: () => getEndpointHealth(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

export function useCheckEndpoints() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => checkApiEndpoints(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitoring', 'endpoint-health'] })
    },
  })
}

export function useWatchdogAlerts(limit = 50, resolved = false) {
  return useQuery({
    queryKey: ['monitoring', 'watchdog-alerts', limit, resolved],
    queryFn: () => getWatchdogAlerts(limit, resolved),
    staleTime: 30_000,
    refetchInterval: 30_000,
  })
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (alertId: string) => acknowledgeAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitoring', 'watchdog-alerts'] })
    },
  })
}

export function useResolveAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ alertId, resolution }: { alertId: string; resolution?: string }) => resolveAlert(alertId, resolution),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitoring', 'watchdog-alerts'] })
    },
  })
}

export function useErrorTrends(hours = 24, source?: string, errorType?: string) {
  return useQuery({
    queryKey: ['monitoring', 'error-trends', hours, source, errorType],
    queryFn: () => getErrorTrends(hours, source, errorType),
    staleTime: 60_000,
    enabled: hours > 0,
  })
}

export function useHealthScore() {
  return useQuery({
    queryKey: ['monitoring', 'health-score'],
    queryFn: () => getHealthScore(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

export function useCrawlerStatus() {
  return useQuery({
    queryKey: ['crawler', 'status'],
    queryFn: () => getCrawlerStatus(),
    staleTime: 10_000,
  })
}

function getCrawlerStatus() {
  return fetchJson<{ running: boolean; queue: { pending: number } }>('/api/v1/crawler/status', true)
}

export function useMonitoringSources() {
  const crawler = useCrawlerStatus()
  const watchdog = useWatchdogHealth()
  const alerts = useMonitorAlerts()
  const stats = useMonitorStats()

  const isLoading = crawler.isLoading || watchdog.isLoading
  const error = crawler.error || watchdog.error

  return {
    isLoading,
    error,
    sources: [
      {
        id: 'crawler',
        label: 'e-GP Crawler',
        status: crawler.data?.running ? 'up' as const : 'down' as const,
        lastCheck: null,
        tendersTracked: stats.data?.tender_count ?? 0,
        alertsActive: alerts.data?.alerts.filter(a => a.severity === 'critical').length ?? 0,
      },
      {
        id: 'watchdog',
        label: 'System Watchdog',
        status: watchdog.data?.status === 'healthy' ? 'up' as const : 'down' as const,
        lastCheck: watchdog.data?.last_check ?? null,
        tendersTracked: stats.data?.entity_count ?? 0,
        alertsActive: watchdog.data?.errors_24h ?? 0,
      },
      {
        id: 'agents',
        label: 'Agent Pipeline',
        status: (crawler.data?.running || (watchdog.data?.status === 'healthy')) ? 'up' as const : 'down' as const,
        lastCheck: null,
        tendersTracked: crawler.data?.queue?.pending ?? 0,
        alertsActive: 0,
      },
    ],
  }
}

