import { fetchJson } from '../sharedApi'
import type { RegisteredAgent, BrainStatus, AgentResultsResponse, PipelinePhase, AgentRunResult } from './types'

const BASE = '/api'

/**
 * Backend shapes (verified against the live FastAPI app):
 *   GET  /api/agents               -> { brain_agents: RegisteredAgent[] }
 *   GET  /api/brain/status         -> { agents_registered, queue_size, knowledge_entries, agents[] }
 *   GET  /api/v1/agent-results/recent?limit= -> { total, results[] }
 *   GET  /api/v1/pipeline/phases   -> { phases: { [name]: { agents: string[], count: number } } }
 *   POST /api/v1/agents/{id}/run   -> AgentRunResult   (POST only; GET returns 404)
 * The helpers below unwrap those envelopes so callers get the flat types.
 */

interface RegisteredAgentsEnvelope {
  brain_agents?: RegisteredAgent[]
  agents?: RegisteredAgent[]
}

export async function getRegisteredAgents(): Promise<RegisteredAgent[]> {
  const data = await fetchJson<RegisteredAgentsEnvelope | RegisteredAgent[]>(`${BASE}/agents`, true)
  if (Array.isArray(data)) return data
  return data.brain_agents ?? data.agents ?? []
}

export function getBrainStatus(): Promise<BrainStatus> {
  return fetchJson<BrainStatus>(`${BASE}/brain/status`, true)
}

export async function getRecentAgentRuns(limit = 50): Promise<AgentRunResult[]> {
  const data = await fetchJson<AgentResultsResponse>(`${BASE}/v1/agent-results/recent?limit=${limit}`, true)
  return data.results ?? []
}

interface PipelinePhasesEnvelope {
  phases?: Record<string, { agents?: string[]; count?: number }>
}

export async function getPipelinePhases(): Promise<PipelinePhase[]> {
  const data = await fetchJson<PipelinePhasesEnvelope | PipelinePhase[]>(`${BASE}/v1/pipeline/phases`, true)
  if (Array.isArray(data)) return data
  return Object.entries(data.phases ?? {}).map(([phase, value]) => ({
    phase,
    agents: value?.agents ?? [],
    status: 'idle' as const,
  }))
}

export function runAgent(agentId: string, context: Record<string, unknown> = {}): Promise<AgentRunResult> {
  return fetchJson<AgentRunResult>(`${BASE}/v1/agents/${agentId}/run`, {
    method: 'POST',
    body: JSON.stringify(context),
    authed: true,
  })
}
