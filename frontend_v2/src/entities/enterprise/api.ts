import { fetchJson } from '../sharedApi'
import type { AuditLogEntry, TeamMember, RoleInfo, EnterpriseCapabilities, TenantInfo } from './types'

const BASE = '/api/v2/enterprise'
let enterpriseTenantPromise: Promise<TenantInfo | null> | null = null

async function getEnterpriseTenant(): Promise<TenantInfo | null> {
  if (!enterpriseTenantPromise) {
    enterpriseTenantPromise = fetchJson<TenantInfo>(`${BASE}/current-tenant`, true)
      .catch(error => {
        enterpriseTenantPromise = null
        throw error
      })
  }
  return enterpriseTenantPromise
}

async function enterpriseTenantId(): Promise<string | null> {
  try {
    const tenant = await getEnterpriseTenant()
    return tenant?.id ?? null
  } catch {
    return null
  }
}

export async function getCapabilities(): Promise<EnterpriseCapabilities | null> {
  try {
    return await fetchJson<EnterpriseCapabilities>(`${BASE}/capabilities`, true)
  } catch {
    return null
  }
}

export async function getAuditLogs(limit = 50): Promise<{ success: boolean; audit_logs: AuditLogEntry[] }> {
  try {
    return await fetchJson<{ success: boolean; audit_logs: AuditLogEntry[] }>(`${BASE}/audit-logs?limit=${limit}`, true)
  } catch {
    return { success: false, audit_logs: [] }
  }
}

export async function getTenantInfo(): Promise<TenantInfo | null> {
  try {
    return await getEnterpriseTenant()
  } catch {
    return null
  }
}

export async function getTeamMembers(): Promise<TeamMember[]> {
  try {
    const tid = await enterpriseTenantId()
    if (!tid) return []
    const data = await fetchJson<Array<{
      member_id: string
      email: string
      full_name?: string | null
      role: string
      joined_at: string
    }>>(`${BASE}/tenants/${encodeURIComponent(tid)}/members`, true)
    return data.map(member => ({
      id: member.member_id,
      email: member.email,
      name: member.full_name ?? member.email,
      role: member.role,
      joined_at: member.joined_at,
    }))
  } catch {
    return []
  }
}

export async function getRoles(): Promise<RoleInfo[]> {
  try {
    const tid = await enterpriseTenantId()
    if (!tid) return []
    const data = await fetchJson<Array<{
      id: string
      name: string
      description?: string | null
      permission_ids: string[]
      is_system: boolean
    }> | { success: boolean; roles: RoleInfo[] }>(`${BASE}/roles?tenant_id=${encodeURIComponent(tid)}`, true)
    if (!Array.isArray(data)) return data.roles
    return data.map(role => ({
      id: role.id,
      name: role.name,
      description: role.description ?? '',
      permissions: role.permission_ids,
      is_system: role.is_system,
    }))
  } catch {
    return []
  }
}
