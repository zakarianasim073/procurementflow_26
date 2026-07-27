import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, CheckCircle, AlertTriangle, Clock, Play, RefreshCw } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { useRegisteredAgents, useBrainStatus, useRecentAgentRuns, usePipelinePhases, useRunAgent } from '@hooks/index'

function PhaseCard({ phase }: { phase: { phase: string; agents: string[]; status: string } }) {
  const statusColor = ({
    idle: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  } as Record<string, string>)[phase.status] || 'bg-gray-100 text-gray-600'

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 capitalize">{phase.phase}</h3>
        <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', statusColor)}>
          {phase.status}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {phase.agents.map(a => (
          <span key={a} className="rounded bg-gray-100 px-2 py-0.5 text-[10px] font-mono text-gray-600 dark:bg-gray-800 dark:text-gray-400">
            {a}
          </span>
        ))}
      </div>
    </div>
  )
}

function AgentCard({ agent, onRun }: { agent: { id: string; name: string; description: string; version: string; available: boolean }; onRun: (id: string) => void }) {
  return (
    <div className={cn(
      'rounded-xl border bg-white p-3 dark:bg-gray-900 transition-opacity',
      agent.available ? 'border-gray-200 dark:border-gray-800' : 'border-gray-100 opacity-50 dark:border-gray-800'
    )}>
      <div className="mb-2 flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{agent.name}</span>
            <span className="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-mono text-gray-500 dark:bg-gray-800 dark:text-gray-400">{agent.id}</span>
          </div>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">{agent.description}</p>
        </div>
        <span className={cn(
          'shrink-0 h-2 w-2 rounded-full mt-1',
          agent.available ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
        )} />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-gray-400">v{agent.version}</span>
        {agent.available && (
          <button
            onClick={() => onRun(agent.id)}
            className="flex items-center gap-1 rounded bg-blue-50 px-2 py-1 text-[10px] font-medium text-blue-600 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/40"
          >
            <Play size={10} /> Run
          </button>
        )}
      </div>
    </div>
  )
}

function AgentRunRow({ run, navigate }: { run: { run_id: string; agent_name: string; agent_id: string; status: string; execution_time_ms: number; timestamp: string; tender_id: string | null; error: string | null }; navigate?: (path: string) => void }) {
  return (
    <>
      <div
        className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800/60 dark:hover:bg-gray-800"
        onClick={() => navigate?.(`/trust/results/${run.run_id}`)}
        role="button"
        tabIndex={0}
      >
        <div className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          run.status === 'completed' && 'bg-green-100 dark:bg-green-900/40',
          run.status === 'running' && 'bg-blue-100 dark:bg-blue-900/40',
          run.status === 'failed' && 'bg-red-100 dark:bg-red-900/40',
          !['completed', 'running', 'failed'].includes(run.status) && 'bg-gray-100 dark:bg-gray-800'
        )}>
          {run.status === 'completed' && <CheckCircle size={14} className="text-green-600 dark:text-green-400" />}
          {run.status === 'running' && <RefreshCw size={14} className="animate-spin text-blue-600 dark:text-blue-400" />}
          {run.status === 'failed' && <AlertTriangle size={14} className="text-red-600 dark:text-red-400" />}
          {!['completed', 'running', 'failed'].includes(run.status) && <Clock size={14} className="text-gray-400" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-900 dark:text-white">{run.agent_name}</span>
            <span className="text-[10px] font-mono text-gray-400">{run.agent_id}</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-gray-500">
            <span>{new Date(run.timestamp).toLocaleString()}</span>
            <span>·</span>
            <span>{(run.execution_time_ms / 1000).toFixed(1)}s</span>
            {run.tender_id && (
              <>
                <span>·</span>
                <span className="font-mono">{run.tender_id}</span>
              </>
            )}
          </div>
          {run.error && <p className="mt-0.5 text-[10px] text-red-500 truncate">{run.error}</p>}
        </div>
        <span className={cn(
          'shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium',
          // Backend emits "success"/"failed"; "completed" kept for older records.
          ['completed', 'success'].includes(run.status) && 'bg-green-100 text-green-700 dark:bg-green-900/40',
          run.status === 'running' && 'bg-blue-100 text-blue-700 dark:bg-blue-900/40',
          run.status === 'failed' && 'bg-red-100 text-red-700 dark:bg-red-900/40',
          !['completed', 'success', 'running', 'failed'].includes(run.status) && 'bg-gray-100 text-gray-500 dark:bg-gray-800'
        )}>{run.status}</span>
      </div>
    </>
  )
}

export function TrustAgentsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<'agents' | 'runs' | 'pipeline'>('agents')
  const agents = useRegisteredAgents()
  const brainStatus = useBrainStatus()
  const recentRuns = useRecentAgentRuns(50)
  const pipelinePhases = usePipelinePhases()
  const runAgent = useRunAgent()

  const handleRunAgent = (agentId: string) => {
    runAgent.mutate({ agentId })
  }

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/40">
              <Bot size={16} className="text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Agent Pipeline</h1>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {brainStatus.isLoading ? 'Loading...' : `${brainStatus.data?.agents_registered ?? '?'} agents · ${brainStatus.data?.knowledge_entries ?? '?'} knowledge entries`}
              </p>
            </div>
          </div>
        </div>
      }
      kpiStrip={
        <div className="grid grid-cols-4 gap-3">
          <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <p className="text-xs text-gray-500">Registered</p>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{brainStatus.data?.agents_registered ?? '-'}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <p className="text-xs text-gray-500">Queue Size</p>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{brainStatus.data?.queue_size ?? '-'}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <p className="text-xs text-gray-500">Knowledge</p>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{brainStatus.data?.knowledge_entries ?? '-'}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <p className="text-xs text-gray-500">Handlers</p>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{brainStatus.data?.message_handlers ?? '-'}</p>
          </div>
        </div>
      }
      primary={
        <div className="space-y-4">
          <div className="flex gap-2 border-b border-gray-200 pb-2 dark:border-gray-700">
            {(['agents', 'runs', 'pipeline'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                  tab === t ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400' : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
                )}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {tab === 'agents' && (
            agents.isLoading ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28 w-full rounded-xl" />)}
              </div>
            ) : agents.data && agents.data.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {agents.data.map(a => <AgentCard key={a.id} agent={a} onRun={handleRunAgent} />)}
              </div>
            ) : (
              <EmptyState title="No agents" description="No agents are registered in the system." />
            )
          )}

          {tab === 'runs' && (
            recentRuns.isLoading ? (
              <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}</div>
            ) : recentRuns.data && recentRuns.data.length > 0 ? (
              <div className="space-y-2">
                {recentRuns.data.map(r => (
                  <AgentRunRow
                    key={r.run_id}
                    run={r}
                    navigate={navigate}
                  />
                ))}
              </div>
            ) : (
              <EmptyState title="No runs" description="No recent agent runs recorded." />
            )
          )}

          {tab === 'pipeline' && (
            pipelinePhases.isLoading ? (
              <div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}</div>
            ) : pipelinePhases.data && pipelinePhases.data.length > 0 ? (
              <div className="space-y-3">
                {pipelinePhases.data.map(p => <PhaseCard key={p.phase} phase={p} />)}
              </div>
            ) : (
              <EmptyState title="No pipeline phases" description="Pipeline phase data is not available." />
            )
          )}
        </div>
      }
      activityTimeline={
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Brain Status</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">Cache</span>
              <span className="font-medium text-gray-900 dark:text-white">{(brainStatus.data?.knowledge_entries ?? 0) > 0 ? `${brainStatus.data?.knowledge_entries} entries` : 'Empty'}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">Queue</span>
              <span className="font-medium text-gray-900 dark:text-white">{brainStatus.data?.queue_size ?? 0} pending</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">Handlers</span>
              <span className="font-medium text-gray-900 dark:text-white">{brainStatus.data?.message_handlers ?? 0}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">Agents</span>
              <span className="font-medium text-gray-900 dark:text-white">{brainStatus.data?.agents_registered ?? 0} registered</span>
            </div>
          </div>
        </div>
      }
    />
  )
}
