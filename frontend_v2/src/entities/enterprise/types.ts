export interface EnterpriseCapabilities {
  api_versions: string[]
  features: Record<string, unknown>
  retention_resource_types: string[]
}

export interface AuditLogEntry {
  id: string
  action: string
  resource_type: string | null
  resource_id: string | null
  status: string
  metadata: Record<string, unknown>
  user_id: string
  tenant_id: string
  created_at: string
}

export interface TenantInfo {
  id: string
  name: string
  slug: string
  plan: string
  created_at: string
  config?: Record<string, any>
}

export interface TeamMember {
  id: string
  email: string
  name: string
  role: string
  joined_at: string
}

export interface RoleInfo {
  id: string
  name: string
  description: string
  permissions: string[]
  is_system: boolean
}
