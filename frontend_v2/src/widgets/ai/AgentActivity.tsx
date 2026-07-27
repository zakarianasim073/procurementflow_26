import { cn } from '@shared/lib/cn'

export interface AgentRun {
  id: string
  agentName: string
  status: 'running' | 'completed' | 'failed'
  startedAt: string
  completedAt?: string
  summary?: string
}

export interface AgentActivityProps {
  runs: AgentRun[]
  className?: string
}

const statusConfig = {
  running: { dot: 'bg-brand-600 animate-pulse dark:bg-brand-400', label: 'Running' },
  completed: { dot: 'bg-success-700 dark:bg-success-300', label: 'Completed' },
  failed: { dot: 'bg-danger-700 dark:bg-danger-300', label: 'Failed' },
}

export function AgentActivity({ runs, className }: AgentActivityProps) {
  if (runs.length === 0) {
    return (
      <div className={cn('rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900', className)}>
        <p className="text-xs text-gray-500 dark:text-gray-400">No agent activity yet.</p>
      </div>
    )
  }

  return (
    <div className={cn('rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900', className)}>
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Agent Activity</p>
      <div className="space-y-2">
        {runs.map((run) => {
          const cfg = statusConfig[run.status]
          return (
            <div key={run.id} className="flex items-start gap-2">
              <span className={cn('mt-1 h-2 w-2 shrink-0 rounded-full', cfg.dot)} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-900 dark:text-white">{run.agentName}</span>
                  <span className="text-[10px] text-gray-400 dark:text-gray-500">{cfg.label}</span>
                </div>
                {run.summary && (
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400 line-clamp-1">{run.summary}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
