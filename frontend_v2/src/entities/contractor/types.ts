export interface ContractorExperienceCategory {
  category: string
  projects_count: number
  avg_value: number
  largest_value: number
  years_active: number
  trend: 'growing' | 'stable' | 'declining'
}

export interface ContractorAward {
  award_id: string
  tender_id: string
  award_date: string
  contract_value: number
  category: string
  status: 'completed' | 'in-progress' | 'cancelled'
}

export interface ContractorOpportunity {
  tender_id: string
  match_score: number
  reason: string
  partner_recommendation?: string
}

export interface ContractorProfile {
  id: string
  name: string
  registration_id: string
  
  // Status
  status: 'active' | 'inactive' | 'suspended'
  years_operating: number
  ppr2025_eligible: boolean
  active_in_egp_last_30d: boolean
  executive_summary?: string
  
  // Experience (from Brain)
  experience: {
    total_years: number
    by_category: ContractorExperienceCategory[]
  }
  
  // Financial (from Brain)
  financial: {
    annual_turnover: number
    cash_position: number
    debt_ratio: number
    financial_trend: 'improving' | 'stable' | 'declining'
  }
  
  // Awards (from NOA + TDR data)
  awards: ContractorAward[]
  
  // Eligibility (computed from Brain.eligibility_check())
  eligibility: {
    rule_37_experience: 'met' | 'gap' | 'exceed'
    rule_38_financial: 'met' | 'gap' | 'exceed'
    rule_40_technical: 'met' | 'gap' | 'exceed'
    missing_categories?: string[]
  }
  
  // Risk (computed by risk_agent)
  risk_profile: {
    compliance_risk: 'low' | 'medium' | 'high'
    market_risk: 'low' | 'medium' | 'high'
    financial_risk: 'low' | 'medium' | 'high'
    operational_risk: 'low' | 'medium' | 'high'
    overall_risk: 'low' | 'medium' | 'high'
    flags: Array<{
      flag: string
      severity: 'low' | 'medium' | 'high'
      recommendation: string
    }>
  }
  
  // Next top opportunities
  next_opportunities?: ContractorOpportunity[]
}

export interface ContractorAwardPaginated {
  awards: ContractorAward[]
  total: number
  page: number
  page_size: number
}
