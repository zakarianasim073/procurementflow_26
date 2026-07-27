export interface RegisteredAgent {
  id: string
  name: string
  description: string
  version: string
  available: boolean
}

export interface BrainStatus {
  agents_registered: number
  queue_size: number
  knowledge_entries: number
  /** Not currently returned by /api/brain/status; UI falls back to 0. */
  message_handlers?: number
}

export interface AgentRunResult {
  run_id: string
  timestamp: string
  tender_id: string | null
  agent_id: string
  agent_name: string
  status: string
  output: Record<string, unknown> | null
  error: string | null
  execution_time_ms: number
}

export interface AgentResultsResponse {
  total: number
  results: AgentRunResult[]
}

export interface PipelinePhase {
  phase: string
  agents: string[]
  status: 'idle' | 'running' | 'completed' | 'failed'
}
