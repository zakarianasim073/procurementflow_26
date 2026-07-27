/** Matches backend SystemStatsResponse (app/api/v2/admin.py) */
export interface AdminStats {
  total_users: number
  total_tenants: number
  total_tenders: number
  total_documents: number
  active_subscriptions: number
  storage_used_gb: number
  uptime_hours: number
}

/** Matches backend AuditLogResponse */
export interface AuditLog {
  id: string
  timestamp: string
  user_id: string
  action: string
  resource_type: string
  resource_id?: string | null
  status: string
  ip_address?: string | null
}

/** GET /api/health — the app-wide health probe */
export interface SystemHealth {
  status: string
  api_routers_loaded?: boolean
  agent_runtime_ready?: boolean
  [key: string]: unknown
}
