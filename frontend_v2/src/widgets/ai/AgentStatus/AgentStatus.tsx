import { useState } from 'react'
import { Bot, CheckCircle, AlertTriangle, XCircle, RefreshCw, Play, Square, Loader2 } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { useRegisteredAgents, useRecentAgentRuns } from '@hooks/index'

interface AgentRow { id: string; name: string; status: 'running' | 'idle' | 'completed' | 'failed'; lastRun: string; duration: string; version: string }

const STATUS_ICONS = { running: AlertTriangle, completed: CheckCircle, failed: XCircle, idle: Bot }
const STATUS_COLORS = { running: 'text-blue-500', completed: 'text-green-500', failed: 'text-red-500', idle: 'text-gray-400' }

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Agent runs from orchestration log', status: 'verified', detail: 'All agents tracked' },
]

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(0)}s`
  const m = Math.floor(ms / 60000)
  const s = Math.floor((ms % 60000) / 1000)
  return `${m}m ${s}s`
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  if (diff < 60000) return 'Now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return `${Math.floor(diff / 86400000)}d ago`
}

export function AgentStatus() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: agents, isLoading: agentsLoading } = useRegisteredAgents()
  const { data: recentRuns, isLoading: runsLoading } = useRecentAgentRuns(50)

  const isLoading = agentsLoading || runsLoading

  const rows: AgentRow[] = (agents ?? []).map((a) => {
    const runs = (recentRuns ?? []).filter((r) => r.agent_id === a.id)
    const latest = runs[0]
    let status: AgentRow['status'] = 'idle'
    if (latest) {
      if (latest.status === 'running') status = 'running'
      else if (latest.status === 'success' || latest.status === 'completed') status = 'completed'
      else if (latest.status === 'failed' || latest.status === 'error') status = 'failed'
    }
    return {
      id: a.id,
      name: a.name,
      status,
      lastRun: latest ? timeAgo(latest.timestamp) : '-',
      duration: latest ? formatDuration(latest.execution_time_ms) : '-',
      version: a.version,
    }
  })

  const counts = { completed: rows.filter((r) => r.status === 'completed').length, running: rows.filter((r) => r.status === 'running').length, failed: rows.filter((r) => r.status === 'failed').length, idle: rows.filter((r) => r.status === 'idle').length }

  return (
    <WidgetContainer>
      <WidgetHeader title="Agent Status" subtitle="AI agent activity monitor" icon={<Bot size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Play size={14} />} label="Run All" />
        <ToolbarButton icon={<Square size={14} />} label="Stop All" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
      </WidgetToolbar>
      <WidgetContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={20} className="animate-spin text-gray-400" />
          </div>
        ) : rows.length === 0 ? (
          <div className="py-8 text-center text-xs text-gray-400">No agents registered</div>
        ) : (
          <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
            {rows.map((agent) => {
              const Icon = STATUS_ICONS[agent.status]
              return (
                <div key={agent.id} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <Icon size={14} className={STATUS_COLORS[agent.status]} />
                    <div>
                      <p className="text-xs font-medium text-gray-900 dark:text-white">{agent.name}</p>
                      <div className="flex items-center gap-2 text-[10px] text-gray-400">
                        <span>v{agent.version}</span>
                        <span>{agent.duration}</span>
                        <span>{agent.lastRun}</span>
                      </div>
                    </div>
                  </div>
                  <Badge variant="outline" className={cn('text-[10px]', agent.status === 'failed' ? 'border-red-200 text-red-600' : agent.status === 'running' ? 'border-blue-200 text-blue-600' : agent.status === 'completed' ? 'border-green-200 text-green-600' : '')}>
                    {agent.status}
                  </Badge>
                </div>
              )
            })}
          </div>
        )}
      </WidgetContent>
      <WidgetFooter>
        <div className="text-[11px] text-gray-500">{counts.idle} idle · {counts.running} running · {counts.failed} failed · {counts.completed} completed</div>
      </WidgetFooter>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Agent Insights" />
      <TrustPanel widgetId="agent-status" widgetTitle="Agent Status" confidence={95} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Agent Status" />
    </WidgetContainer>
  )
}