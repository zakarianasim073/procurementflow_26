/**
 * DEPRECATED shim. The original implementation used a raw unauthenticated
 * fetch against /api/v1/agents/brain-status. Routed through ./useAgents so all
 * agent calls share one authed client.
 */
export { useBrainStatus } from './useAgents'
