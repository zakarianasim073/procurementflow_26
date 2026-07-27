export interface ComplianceRule {
  rule_id: string
  rule_code: string
  title: string
  description: string
  category: string
  status: 'pass' | 'fail' | 'warning' | 'pending'
  details?: string
  version: string
  updated_at: string
}

export interface ComplianceCheck {
  check_id: string
  tender_id: string
  rules: ComplianceRule[]
  overall_status: 'compliant' | 'non_compliant' | 'partial'
  score: number
  checked_at: string
}

export interface TDSCriteria {
  general_experience: string | null
  specific_experience_value: number | null
  specific_experience_count: number | null
  avg_annual_turnover: number | null
  liquid_assets: number | null
  min_tender_capacity: number | null
  tender_security: number | null
  performance_security: number | null
  retention_money: number | null
}
