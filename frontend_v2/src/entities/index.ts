export * from './executive'
export * from './tender'
export * from './opportunity'
export * from './qualification'
export * from './monitoring'
export * from './chat'
export * from './agents'
// Disambiguate: both './opportunity' and './agents' export AgentResultsResponse.
// The agents variant is the one consumed by name (useAgents hook); make it win.
export type { AgentResultsResponse } from './agents'
export * from './enterprise'
export * from './clause'
export * from './clauseTree'
export * from './ruleGraph'
export * from './roi'
export * from './contractor'
export * from './pricing'
export { type RegisteredAgent, type BrainStatus, type AgentRunResult, type PipelinePhase } from './agents'
export { getRegisteredAgents, getBrainStatus, getRecentAgentRuns, getPipelinePhases, runAgent } from './agents'
export { type FeedbackEntry, type FeedbackStats, type FeedbackAwaitingItem, type FeedbackSubmitResult, type FeedbackSubmitPayload } from './feedback'

// Phase 2 API Entities.
// `admin` is exported explicitly (not star) because `getAuditLogs` and `AuditLog`
// also exist in `./enterprise`; the Phase 2 ones are suffixed to disambiguate.
export * from './intelligence'
export * from './documents'
export * from './team'
export {
  getAdminStats,
  getSystemHealth,
  getAuditLogs as getAdminAuditLogs,
} from './admin'
export type {
  AdminStats,
  SystemHealth,
  AuditLog as AdminAuditLog,
} from './admin'