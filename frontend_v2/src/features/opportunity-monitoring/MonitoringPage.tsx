import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wifi, WifiOff, RefreshCw, AlertTriangle, CheckCircle, Activity, Clock, Monitor, Shield, FileText, Zap, Bell, TrendingUp, Eye, Check, X } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { cn } from '@shared/lib/cn'
import { useMonitoringSources, useMonitorAlerts, useWatchdogErrors, useAgencies, useOpeningReports, useSystemMetrics, useEndpointHealth, useWatchdogAlerts, useHealthScore, useErrorTrends, useCheckEndpoints } from '@hooks/index'
import { AgencyBreakdown, OpeningReports } from '@widgets/opportunity/index'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { acknowledgeAlert, resolveAlert, checkApiEndpoints } from '@entities/monitoring'
import type { WatchdogAlert } from '@entities/monitoring'

// Prop type interfaces to avoid inline object types causing brace imbalance
interface StatusBadgeProps {
  status: 'up' | 'down' | 'loading'
}

interface MonitorTileProps {
  source: {
    id: string
    label: string
    status: 'up' | 'down' | 'loading'
    lastCheck: string | null
    tendersTracked: number
    alertsActive: number
  }
}

interface AlertItemProps {
  alert: {
    id: string
    alert_type: string
    title: string
    message: string
    severity: string
    timestamp: string
    read?: boolean
  }
}

interface WatchdogErrorRowProps {
  err: {
    id: string
    source: string
    error_type: string
    error_message: string
    severity: string
    timestamp: string
    resolved: boolean
  }
}

function StatusBadge({ status }: StatusBadgeProps) {
  if (status === 'loading') return <Skeleton className="h-5 w-16 rounded-full" />
  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
      status === 'up' && 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
      status === 'down' && 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'
    )} role="status">
      {status === 'up' ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
      {status === 'up' ? 'Operational' : 'Down'}
    </span>
  )
}

function MonitorTile({ source }: MonitorTileProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{source.label}</h3>
        <StatusBadge status={source.status} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
          <span className="text-xs text-gray-500 dark:text-gray-400">Tenders</span>
          <p className="text-lg font-bold tabular-nums text-gray-900 dark:text-white">{source.tendersTracked}</p>
        </div>
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
          <span className="text-xs text-gray-500 dark:text-gray-400">Alerts</span>
          <p className="text-lg font-bold tabular-nums text-gray-900 dark:text-white">{source.alertsActive}</p>
        </div>
      </div>
      {source.lastCheck && (
        <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
          Last check: {new Date(source.lastCheck).toLocaleString()}
        </p>
      )}
    </div>
  )
}

function AlertItem({ alert }: AlertItemProps) {
  const severityColor = ({
    info: 'border-l-blue-500 bg-blue-50 dark:bg-blue-950/20',
    warning: 'border-l-yellow-500 bg-yellow-50 dark:bg-yellow-950/20',
    critical: 'border-l-red-500 bg-red-50 dark:bg-red-950/20',
  } as Record<string, string>)[alert.severity] || 'border-l-gray-500'

  const severityIcon = ({
    info: <Activity size={14} className="text-blue-500" />,
    warning: <AlertTriangle size={14} className="text-yellow-500" />,
    critical: <AlertTriangle size={14} className="text-red-500" />,
  } as Record<string, any>)[alert.severity] || <Activity size={14} />

  return (
    <div className={cn('border-l-4 rounded-r-lg border border-gray-200 p-3 dark:border-gray-700', severityColor)}>
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0">{severityIcon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-900 dark:text-white">{alert.title}</span>
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              {alert.alert_type}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-400">{alert.message}</p>
          <p className="mt-1 text-[10px] text-gray-400">{new Date(alert.timestamp).toLocaleString()}</p>
        </div>
      </div>
    </div>
  )
}

function WatchdogErrorRow({ err }: WatchdogErrorRowProps) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn(
            'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium',
            err.severity === 'critical' && 'bg-red-100 text-red-700 dark:bg-red-900/40',
            err.severity === 'high' && 'bg-orange-100 text-orange-700 dark:bg-orange-900/40',
            err.severity === 'medium' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40',
            err.severity === 'low' && 'bg-blue-100 text-blue-700 dark:bg-blue-900/40',
          )}>{err.severity}</span>
          <span className="text-xs font-mono text-gray-500">{err.source}</span>
          {err.resolved && <CheckCircle size={12} className="text-green-500" />}
        </div>
        <p className="mt-1 text-xs text-gray-700 dark:text-gray-300">{err.error_type}: {err.error_message}</p>
        <p className="mt-0.5 text-[10px] text-gray-400">{new Date(err.timestamp).toLocaleString()}</p>
      </div>
    </div>
  )
}

function MetricCard({ label, value, icon, color }: { label: string; value: string; icon: ReactNode; color: 'orange' | 'blue' | 'purple' | 'green' }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className={cn('mb-2 flex items-center gap-2 text-xs', color === 'green' ? 'text-green-600' : color === 'orange' ? 'text-orange-600' : color === 'purple' ? 'text-purple-600' : 'text-blue-600')}>
        {icon}{label}
      </div>
      <p className="text-lg font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

function AlertItemV2({ alert, onAcknowledge, onResolve }: { alert: WatchdogAlert; onAcknowledge: (id: string) => void; onResolve: (id: string) => void }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
      <p className="text-xs font-medium text-gray-900 dark:text-white">{alert.category}</p>
      <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{alert.message}</p>
      <div className="mt-2 flex gap-2">
        {!alert.acknowledged && <button onClick={() => onAcknowledge(alert.id)} className="text-xs text-blue-600">Acknowledge</button>}
        {!alert.resolved && <button onClick={() => onResolve(alert.id)} className="text-xs text-green-600">Resolve</button>}
      </div>
    </div>
  )
}

export function MonitoringPage() {
  const [tab, setTab] = useState<'sources' | 'alerts' | 'errors' | 'agencies' | 'metrics' | 'endpoints' | 'health' | 'trends' | 'alerts-v2'>('sources')
  const sources = useMonitoringSources()
  const alerts = useMonitorAlerts(20)
  const errors = useWatchdogErrors(10)
  const agencies = useAgencies()
  const openingReports = useOpeningReports(10)
  const metrics = useSystemMetrics()
  const endpointHealth = useEndpointHealth()
  const watchdogAlerts = useWatchdogAlerts(50, false)
  const healthScore = useHealthScore()
  const errorTrends = useErrorTrends(24)
  const checkEndpoints = useCheckEndpoints()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const acknowledgeMutation = useMutation({ mutationFn: acknowledgeAlert })
  const resolveMutation = useMutation({ mutationFn: ({ alertId, resolution }: { alertId: string; resolution?: string }) => resolveAlert(alertId, resolution) })

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">System Monitoring v2.1</h1>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
              {sources.isLoading ? 'Checking system status...' : `${sources.sources.filter(s => s.status === 'up').length}/${sources.sources.length} services operational • Health: ${healthScore.data?.health_score ?? '—'}%`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => checkEndpoints.mutate(undefined, { onSuccess: () => queryClient.invalidateQueries({ queryKey: ['monitoring', 'endpoint-health'] }) })}
              disabled={checkEndpoints.isPending}
              className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              <RefreshCw size={14} className={cn('inline mr-1', checkEndpoints.isPending && 'animate-spin')} /> Check Endpoints
            </button>
            <button
              onClick={() => { if (sources.error) window.location.reload() }}
              className="rounded-lg border border-gray-200 bg-white p-2 text-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-800"
              aria-label="Refresh"
            >
              <RefreshCw size={16} className={cn(sources.isLoading && 'animate-spin')} />
            </button>
          </div>
        </div>
      }
      kpiStrip={
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Monitor size={14} /> Sources
            </div>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{sources.sources.length}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Bell size={14} /> Alerts
            </div>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{watchdogAlerts.data?.length ?? alerts.data?.total ?? '-'}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Shield size={14} /> Health
            </div>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">
              {healthScore.data?.health_score !== undefined ? `${healthScore.data.health_score}% (${healthScore.data.status})` : (sources.sources.filter(s => s.status === 'up').length === sources.sources.length ? '100%' : `${Math.round(sources.sources.filter(s => s.status === 'up').length / sources.sources.length * 100)}%`)}
            </p>
          </div>
        </div>
      }
      primary={
        <div className="space-y-4">
          <div className="flex gap-2 border-b border-gray-200 pb-2 dark:border-gray-700 flex-wrap">
            {(['sources', 'alerts', 'errors', 'agencies', 'metrics', 'endpoints', 'health', 'trends', 'alerts-v2'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                  tab === t ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400' : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
                )}
              >
                {t === 'agencies' ? 'Agencies' : t === 'alerts-v2' ? 'Alerts v2' : t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {tab === 'sources' && (
            sources.isLoading ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 w-full rounded-xl" />)}
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {sources.sources.map(s => <MonitorTile key={s.id} source={s} />)}
              </div>
            )
          )}

          {tab === 'alerts' && (
            alerts.isLoading ? (
              <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}</div>
            ) : alerts.data && alerts.data.alerts.length > 0 ? (
              <div className="space-y-2">
                {alerts.data.alerts.map(a => <AlertItem key={a.id} alert={a} />)}
              </div>
            ) : (
              <EmptyState title="No alerts" description="All systems operating normally." />
            )
          )}

          {tab === 'alerts-v2' && (
            watchdogAlerts.isLoading ? (
              <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}</div>
            ) : watchdogAlerts.data && watchdogAlerts.data.length > 0 ? (
              <div className="space-y-2">
                {watchdogAlerts.data.map(a => (
                  <AlertItemV2
                    key={a.id}
                    alert={a}
                    onAcknowledge={(id) => acknowledgeMutation.mutate(id)}
                    onResolve={(id) => resolveMutation.mutate({ alertId: id })}
                  />
                ))}
              </div>
            ) : (
              <EmptyState title="No watchdog alerts" description="All systems operating normally." />
            )
          )}

          {tab === 'errors' && (
            errors.isLoading ? (
              <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}</div>
            ) : errors.data && errors.data.length > 0 ? (
              <div className="space-y-2">
                {errors.data.map((e, i) => <WatchdogErrorRow key={e.id ?? `error-${i}`} err={e} />)}
              </div>
            ) : (
              <EmptyState title="No errors" description="No system errors recorded." />
            )
          )}

          {tab === 'agencies' && (
            <AgencyBreakdown agencies={agencies.data?.agencies ?? []} isLoading={agencies.isLoading} />
          )}

          {tab === 'metrics' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard label="CPU Usage" value={`${metrics.data?.cpu_percent ?? 0}%`} icon={<Activity size={20} />} color="orange" />
                <MetricCard label="Memory" value={`${metrics.data?.memory_percent ?? 0}% (${metrics.data?.memory_used_mb ?? 0}MB / ${metrics.data?.memory_total_mb ?? 0}MB)`} icon={<Monitor size={20} />} color="blue" />
                <MetricCard label="Disk" value={`${metrics.data?.disk_percent ?? 0}% (${metrics.data?.disk_used_gb ?? 0}GB / ${metrics.data?.disk_total_gb ?? 0}GB)`} icon={<FileText size={20} />} color="purple" />
                <MetricCard label="Uptime" value={`${Math.floor((metrics.data?.uptime_s ?? 0) / 3600)}h ${Math.floor(((metrics.data?.uptime_s ?? 0) % 3600) / 60)}m`} icon={<Clock size={20} />} color="green" />
              </div>
              <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">System Metrics</h3>
                {metrics.isLoading ? (
                  <Skeleton className="h-32 w-full rounded-lg" />
                ) : metrics.data && metrics.data.timestamp ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                      <span>{new Date(metrics.data.timestamp).toLocaleTimeString()}</span>
                      <span>CPU: {metrics.data.cpu_percent}% | Mem: {metrics.data.memory_percent}% | Disk: {metrics.data.disk_percent}%</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">No metrics available</p>
                )}
              </div>
            </div>
          )}

          {tab === 'endpoints' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">API Endpoint Health</h3>
                <button
                  onClick={() => checkEndpoints.mutate(undefined, { onSuccess: () => queryClient.invalidateQueries({ queryKey: ['monitoring', 'endpoint-health'] }) })}
                  disabled={checkEndpoints.isPending}
                  className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 disabled:opacity-50"
                >
                  <RefreshCw size={14} className={cn('inline mr-1', checkEndpoints.isPending && 'animate-spin')} /> Check Now
                </button>
              </div>
              <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900 overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-gray-800/50">
                      <th className="px-3 py-2 text-left text-gray-500">Endpoint</th>
                      <th className="px-3 py-2 text-left text-gray-500">Status</th>
                      <th className="px-3 py-2 text-left text-gray-500">Response Time</th>
                      <th className="px-3 py-2 text-left text-gray-500">Avg Response</th>
                      <th className="px-3 py-2 text-left text-gray-500">Success / Fail</th>
                      <th className="px-3 py-2 text-left text-gray-500">Last Checked</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(endpointHealth.data ?? {}).map(([key, eh]) => (
                      <tr key={key} className="border-t border-gray-100 dark:border-gray-800">
                        <td className="px-3 py-2 font-mono">{eh.method} {eh.path}</td>
                        <td className="px-3 py-2">
                          <span className={cn(
                            'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium',
                            eh.status === 'healthy' && 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
                            eh.status === 'degraded' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
                            eh.status === 'down' && 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'
                          )}>
                            {eh.status === 'healthy' ? <CheckCircle size={10} className="mr-1" /> : eh.status === 'degraded' ? <AlertTriangle size={10} className="mr-1" /> : <X size={10} className="mr-1" />}
                            {eh.status}
                          </span>
                        </td>
                        <td className="px-3 py-2">{eh.response_time_ms}ms</td>
                        <td className="px-3 py-2">{eh.avg_response_time_ms}ms</td>
                        <td className="px-3 py-2">{eh.success_count} / {eh.failure_count}</td>
                        <td className="px-3 py-2 text-gray-400">{eh.last_checked ? new Date(eh.last_checked).toLocaleTimeString() : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === 'health' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <MetricCard label="Overall Score" value={`${healthScore.data?.health_score ?? 0}%`} icon={<Shield size={20} />} color={(healthScore.data?.health_score ?? 0) >= 90 ? 'green' : (healthScore.data?.health_score ?? 0) >= 70 ? 'blue' : 'orange'} />
                <MetricCard label="Status" value={healthScore.data?.status ?? '—'} icon={<Activity size={20} />} color="blue" />
                <MetricCard label="Agents" value={`${healthScore.data?.breakdown?.agents?.healthy ?? 0}/${(healthScore.data?.breakdown?.agents?.healthy ?? 0) + (healthScore.data?.breakdown?.agents?.degraded ?? 0) + (healthScore.data?.breakdown?.agents?.down ?? 0)}`} icon={<Monitor size={20} />} color="green" />
                <MetricCard label="Database" value={healthScore.data?.breakdown?.database?.status === 'ok' ? 'OK' : 'Issue'} icon={<FileText size={20} />} color={healthScore.data?.breakdown?.database?.status === 'ok' ? 'green' : 'orange'} />
                <MetricCard label="API Endpoints" value={`${Object.values(healthScore.data?.breakdown?.api ?? {}).filter(e => e.status === 'healthy').length}/${Object.keys(healthScore.data?.breakdown?.api ?? {}).length}`} icon={<Zap size={20} />} color="purple" />
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                  <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Recommendations</h3>
                  <ul className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                    {healthScore.data?.breakdown?.recommendations?.map((r, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-orange-500">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                    {(!healthScore.data?.breakdown?.recommendations || healthScore.data.breakdown.recommendations.length === 0) && (
                      <li className="text-green-500">All systems healthy - no recommendations</li>
                    )}
                  </ul>
                </div>
                <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                  <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Pipeline Health</h3>
                  <div className="space-y-2 text-xs text-gray-600 dark:text-gray-400">
                    <div className="flex justify-between"><span>Total Runs</span><span className="font-medium">{healthScore.data?.breakdown?.pipeline?.total ?? 0}</span></div>
                    <div className="flex justify-between"><span>Success Rate</span><span className="font-medium">{healthScore.data?.breakdown?.pipeline?.success_rate ?? 0}%</span></div>
                    <div className="flex justify-between"><span>Failures</span><span className="font-medium">{healthScore.data?.breakdown?.pipeline?.failures ?? 0}</span></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {tab === 'trends' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Error Trends (Last 24h)</h3>
              <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900 overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-gray-800/50">
                      <th className="px-3 py-2 text-left text-gray-500">Source</th>
                      <th className="px-3 py-2 text-left text-gray-500">Error Type</th>
                      <th className="px-3 py-2 text-left text-gray-500">Occurrences</th>
                      <th className="px-3 py-2 text-left text-gray-500">Last Seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {errorTrends.data?.map((t, i) => (
                      <tr key={i} className="border-t border-gray-100 dark:border-gray-800">
                        <td className="px-3 py-2 font-mono">{t.source}</td>
                        <td className="px-3 py-2">{t.error_type}</td>
                        <td className="px-3 py-2 font-medium">{t.occurrences}</td>
                        <td className="px-3 py-2 text-gray-400">{new Date(t.last_seen).toLocaleString()}</td>
                      </tr>
                    ))}
                    {(!errorTrends.data || errorTrends.data.length === 0) && (
                      <tr>
                        <td colSpan={4} className="px-3 py-4 text-center text-gray-400">No error trends in the last 24h</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === 'agencies' && (
            <AgencyBreakdown agencies={agencies.data?.agencies ?? []} isLoading={agencies.isLoading} />
          )}
        </div>
      }
      aiDock={
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <Clock size={14} /> Agent Activity
          </h2>
          <div className="space-y-2">
            {sources.isLoading ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)
            ) : (
              <div className="text-center py-6">
                <Activity size={24} className="mx-auto mb-2 text-gray-300 dark:text-gray-600" />
                <p className="text-xs text-gray-400">Recent agent runs shown here</p>
                <button
                  onClick={() => navigate('/trust/agents')}
                  className="mt-2 text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
                >
                  View all agents
                </button>
              </div>
            )}
          </div>
        </div>
      }
      activityTimeline={
        <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
          <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <FileText size={14} /> Recent Openings
            </h2>
          </div>
          <OpeningReports items={openingReports.data?.reports ?? []} isLoading={openingReports.isLoading} />
        </div>
      }
    />
  )
}
