export interface MonitorStats {
  success: boolean
  tender_count: number
  entity_count: number
  scanned: number
  alerts: number
}

export interface MonitorAlert {
  id: string
  alert_type: string
  tender_id: string
  title: string
  message: string
  severity: 'info' | 'warning' | 'critical'
  timestamp: string
  read: boolean
}

export interface MonitorAlertsResponse {
  alerts: MonitorAlert[]
  total: number
}

export interface MonitorConfig {
  enabled: boolean
  scan_interval_minutes: number
  agencies: string[]
  min_value_bdt: number
}

export interface WatchdogHealth {
  status: 'healthy' | 'degraded' | 'down'
  agents_total: number
  agents_healthy: number
  errors_24h: number
  last_check: string
}

export interface WatchdogError {
  id: string
  source: string
  error_type: string
  error_message: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  timestamp: string
  resolved: boolean
}

export interface MonitorSource {
  id: string
  label: string
  status: 'up' | 'down' | 'loading'
  lastCheck: string | null
  tendersTracked: number
  alertsActive: number
}

// v2.1 Enhanced types
export interface SystemMetrics {
  timestamp: string
  cpu_percent: number
  memory_percent: number
  memory_used_mb: number
  memory_total_mb: number
  disk_percent: number
  disk_used_gb: number
  disk_total_gb: number
  network_io_bytes_sent: number
  network_io_bytes_recv: number
  process_count: number
  uptime_s: number
}

export interface EndpointHealth {
  path: string
  method: string
  status: 'healthy' | 'degraded' | 'down'
  response_time_ms: number
  avg_response_time_ms: number
  last_checked: string
  error: string
  success_count: number
  failure_count: number
}

export interface WatchdogAlert {
  id: string
  timestamp: string
  severity: 'info' | 'warning' | 'critical'
  category: string
  message: string
  details: Record<string, any>
  resolved: boolean
  resolved_at: string
  acknowledged: boolean
}

export interface ErrorTrend {
  source: string
  error_type: string
  occurrences: number
  last_seen: string
  trend_points: Array<{ timestamp: string; count: number }>
}

export interface HealthScore {
  health_score: number
  status: 'healthy' | 'degraded' | 'critical' | 'emergency'
  breakdown: HealthScoreBreakdown
}

export interface HealthScoreBreakdown {
  agents: { healthy: number; degraded: number; down: number; details: Record<string, string> }
  database: { status: string; size_mb: number; issues: string[] }
  system: { cpu_percent: number; memory_percent: number; disk_percent: number; uptime_s: number }
  api: Record<string, { status: string; response_time_ms: number; avg_response_time_ms: number }>
  pipeline: { total: number; success_rate: number; failures: number; by_stage: Record<string, number> }
  recent_errors: Array<{ id: string; source: string; type: string; severity: string; message: string; count: number }>
  error_count: number
  active_alerts: Array<any>
  recommendations: string[]
}
