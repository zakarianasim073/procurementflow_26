/** Matches backend TeamMemberResponse (app/api/v2/team.py) */
export interface TeamMemberRole {
  id: string
  tenant_id: string
  email: string
  full_name: string
  role: 'owner' | 'admin' | 'member' | 'viewer'
  department?: string | null
  phone?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

/** Matches backend TeamResponse — returned flat, not wrapped */
export interface TeamInfo {
  id: string
  tenant_id: string
  name: string
  max_members: number
  member_count: number
  members: TeamMemberRole[]
  created_at: string
  updated_at: string
}

export interface InviteTeamMemberPayload {
  email: string
  full_name: string
  role: 'admin' | 'member' | 'viewer'
  department?: string
  phone?: string
}

export interface UpdateTeamMemberPayload {
  full_name?: string
  role?: 'admin' | 'member' | 'viewer'
  department?: string
  phone?: string
  is_active?: boolean
}
