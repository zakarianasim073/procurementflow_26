import { getAuthToken } from '../authToken'
import { authReady } from '../bootstrapAuth'
import type {
  TeamInfo,
  TeamMemberRole,
  InviteTeamMemberPayload,
  UpdateTeamMemberPayload,
} from './types'

const BASE = '/api/v2/team'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  await authReady()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, { headers, ...options })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}

/** GET /api/v2/team — returns the team object directly */
export function getTeam(): Promise<TeamInfo> {
  return fetchJson<TeamInfo>(BASE)
}

/** GET /api/v2/team/members — returns a bare array */
export function listTeamMembers(): Promise<TeamMemberRole[]> {
  return fetchJson<TeamMemberRole[]>(`${BASE}/members`)
}

export function getTeamMember(memberId: string): Promise<TeamMemberRole> {
  return fetchJson<TeamMemberRole>(`${BASE}/members/${memberId}`)
}

export function inviteTeamMember(data: InviteTeamMemberPayload): Promise<TeamMemberRole> {
  return fetchJson<TeamMemberRole>(`${BASE}/members`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateTeamMember(
  memberId: string,
  data: UpdateTeamMemberPayload,
): Promise<TeamMemberRole> {
  return fetchJson<TeamMemberRole>(`${BASE}/members/${memberId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function removeTeamMember(memberId: string): Promise<void> {
  return fetchJson<void>(`${BASE}/members/${memberId}`, { method: 'DELETE' })
}
