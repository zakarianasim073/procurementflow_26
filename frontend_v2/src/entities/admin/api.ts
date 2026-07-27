import { getAuthToken } from '../authToken'
import { authReady } from '../bootstrapAuth'
import type { AdminStats, AuditLog, SystemHealth } from './types'

const BASE = '/api/v2/admin'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  await authReady()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, { headers, ...options })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}

/** GET /api/v2/admin/stats — returns the stats object directly */
export function getAdminStats(): Promise<AdminStats> {
  return fetchJson<AdminStats>(`${BASE}/stats`)
}

/** GET /api/v2/admin/audit-logs — returns a bare array */
export function getAuditLogs(skip = 0, limit = 50): Promise<AuditLog[]> {
  const qs = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  return fetchJson<AuditLog[]>(`${BASE}/audit-logs?${qs.toString()}`)
}

/** GET /api/health — app-wide health, not under /admin */
export function getSystemHealth(): Promise<SystemHealth> {
  return fetchJson<SystemHealth>('/api/health')
}
