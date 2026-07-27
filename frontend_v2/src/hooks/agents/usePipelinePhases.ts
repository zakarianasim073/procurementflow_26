/**
 * DEPRECATED shim. The original implementation used a raw unauthenticated
 * fetch against /api/v1/agents/pipeline-phases and returned the raw
 * `{ phases: {...} }` envelope instead of a PipelinePhase[].
 */
export { usePipelinePhases } from './useAgents'
