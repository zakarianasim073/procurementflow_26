/**
 * DEPRECATED shim.
 *
 * This file used to call `fetch('/api/v1/agents/{id}/run')` directly with no
 * Authorization header and no HTTP method — the backend requires POST + a JWT,
 * so every call 404'd/401'd. Re-exported from ./useAgents (which goes through
 * entities/agents/api.ts -> fetchJson with authed: true) so no caller can
 * accidentally pick up the broken implementation.
 */
export { useRunAgent } from './useAgents'
