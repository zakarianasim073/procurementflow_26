import { useState, useMemo } from 'react'
import { AlertCircle, CheckCircle, Zap, Search } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { useAgents } from '@hooks/agents'

function getPhaseFromId(id: string): string {
  const parts = id.split('-')
  return parts.length >= 2 ? parts[1] : 'unknown'
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  return `${hrs}h ago`
}

interface Agent {
  id: string
  name: string
  version: string
  status: 'healthy' | 'warning' | 'error'
  lastRun: string
  executionTime: number
  phase: string
}

export function AgentsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPhase, setSelectedPhase] = useState<string>('all')
  const [selectedStatus, setSelectedStatus] = useState<string>('all')

  const { registeredAgents, isRegisteredAgentsLoading, recentAgentRuns } = useAgents()

  const lastRunByAgent = useMemo(() => {
    const map = new Map<string, { ts: string; ms: number; status: string }>()
    for (const run of recentAgentRuns) {
      const key = run.agent_id
      if (!map.has(key) || new Date(run.timestamp) > new Date(map.get(key)!.ts)) {
        map.set(key, { ts: run.timestamp, ms: run.execution_time_ms, status: run.status })
      }
    }
    return map
  }, [recentAgentRuns])

  const agents: Agent[] = useMemo(() =>
    registeredAgents.map((a) => {
      const lastRun = lastRunByAgent.get(a.id)
      return {
        id: a.id,
        name: a.name,
        version: a.version,
        status: a.available ? (lastRun?.status === 'failed' ? 'error' as const : 'healthy' as const) : 'error' as const,
        lastRun: lastRun ? timeAgo(lastRun.ts) : 'never',
        executionTime: lastRun?.ms ?? 0,
        phase: getPhaseFromId(a.id),
      }
    }),
  [registeredAgents, lastRunByAgent])

  const phases = ['all', ...new Set(agents.map((a) => a.phase))]
  const statuses = ['all', 'healthy', 'warning', 'error']

  const filteredAgents = agents.filter((agent) => {
    const matchesSearch = agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          agent.id.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesPhase = selectedPhase === 'all' || agent.phase === selectedPhase
    const matchesStatus = selectedStatus === 'all' || agent.status === selectedStatus
    return matchesSearch && matchesPhase && matchesStatus
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle size={16} className="text-green-600 dark:text-green-400" />
      case 'warning':
        return <AlertCircle size={16} className="text-amber-600 dark:text-amber-400" />
      case 'error':
        return <AlertCircle size={16} className="text-red-600 dark:text-red-400" />
      default:
        return null
    }
  }

  const healthyCount = agents.filter(a => a.status === 'healthy').length
  const warningCount = agents.filter(a => a.status === 'warning').length
  const errorCount = agents.filter(a => a.status === 'error').length

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <Zap className="h-6 w-6 text-purple-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agent Management</h1>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">Monitor and manage all {agents.length} procurement agents</p>
          </div>
        </div>
      }
      primary={
        <div className="space-y-6">
          {isRegisteredAgentsLoading ? (
            <div className="flex items-center justify-center h-32"><p className="text-sm text-gray-500">Loading agents...</p></div>
          ) : (
          <>
          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
              <p className="text-xs text-gray-600 dark:text-gray-400">Total Agents</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{agents.length}</p>
            </div>
            <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950/30">
              <p className="text-xs text-green-600 dark:text-green-400">Healthy</p>
              <p className="mt-1 text-2xl font-bold text-green-900 dark:text-green-300">{healthyCount}</p>
            </div>
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
              <p className="text-xs text-amber-600 dark:text-amber-400">Warnings</p>
              <p className="mt-1 text-2xl font-bold text-amber-900 dark:text-amber-300">{warningCount}</p>
            </div>
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/30">
              <p className="text-xs text-red-600 dark:text-red-400">Errors</p>
              <p className="mt-1 text-2xl font-bold text-red-900 dark:text-red-300">{errorCount}</p>
            </div>
          </div>

          {/* Filters */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white">Search Agents</label>
              <div className="relative mt-2">
                <Search size={18} className="absolute left-3 top-2.5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-white">Phase</label>
                <select
                  value={selectedPhase}
                  onChange={(e) => setSelectedPhase(e.target.value)}
                  className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                >
                  {phases.map((phase) => (
                    <option key={phase} value={phase}>
                      {phase === 'all' ? 'All Phases' : phase.charAt(0).toUpperCase() + phase.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-white">Status</label>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                >
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status === 'all' ? 'All Statuses' : status.charAt(0).toUpperCase() + status.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Agents Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">Agent</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">Phase</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">Last Run</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">Execution Time</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-900 dark:text-white">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAgents.map((agent) => (
                  <tr key={agent.id} className="border-b border-gray-200 dark:border-gray-700">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">{agent.name}</p>
                        <p className="text-xs text-gray-500">{agent.id}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(agent.status)}
                        <span className="capitalize text-sm text-gray-600 dark:text-gray-400">{agent.status}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-block rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950/30 dark:text-blue-400">
                        {agent.phase}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{agent.lastRun}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{(agent.executionTime / 1000).toFixed(1)}s</td>
                    <td className="px-4 py-3 text-right">
                      <button className="text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300">
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredAgents.length === 0 && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center dark:border-gray-700 dark:bg-gray-800">
              <p className="text-gray-600 dark:text-gray-400">No agents found matching your criteria</p>
            </div>
          )}
          </>)}
        </div>
      }
    />
  )
}
