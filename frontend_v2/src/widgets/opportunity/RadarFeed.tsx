import { CheckCircle, XCircle, Clock, AlertTriangle, Loader2 } from 'lucide-react'
import type { AgentResultItem } from '@entities/index'

interface RadarFeedProps {
  results: AgentResultItem[]
  isLoading?: boolean
}

function statusIcon(status: string) {
  switch (status) {
    case 'success': return CheckCircle
    case 'failed': case 'error': return XCircle
    case 'running': return Loader2
    case 'pending': return Clock
    default: return AlertTriangle
  }
}

function statusColor(status: string) {
  switch (status) {
    case 'success': return 'text-green-500'
    case 'failed': case 'error': return 'text-red-500'
    case 'running': return 'text-blue-500'
    case 'pending': return 'text-yellow-500'
    default: return 'text-gray-400'
  }
}

function timeAgo(ts: string): string {
  const secs = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (secs < 60) return `${secs}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
  return `${Math.floor(secs / 86400)}d ago`
}

export function RadarFeed({ results, isLoading }: RadarFeedProps) {
  if (isLoading) {
    return <div className="h-48 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
  }

  if (results.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 text-center dark:border-gray-800 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No radar data yet. Start scanning tenders.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Agent Radar Feed</h2>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {results.map((r) => {
          const Icon = statusIcon(r.status)
          return (
            <div key={r.run_id} className="flex items-start gap-3 px-4 py-2.5 text-sm">
              <Icon size={14} className={`mt-0.5 shrink-0 ${statusColor(r.status)} ${r.status === 'running' ? 'animate-spin' : ''}`} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-800 dark:text-gray-200">{r.agent_name}</span>
                  {r.tender_id && (
                    <span className="font-mono text-[10px] text-gray-400">{r.tender_id}</span>
                  )}
                </div>
                {r.error && <p className="mt-0.5 text-xs text-red-500">{r.error}</p>}
              </div>
              <span className="shrink-0 text-xs text-gray-400">{timeAgo(r.timestamp)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
