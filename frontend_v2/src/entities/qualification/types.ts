export interface CapacityInfo {
  total_contracts: number
  total_amount_bdt: number
  last_5yr_awarded_amount_bdt: number
  work_in_hand_bdt: number
  estimated_turnover_bdt: number
  tender_capacity_bdt: number
  utilization_ratio: number
  capacity_status: 'overloaded' | 'tight' | 'available'
  agencies_worked: string[]
  districts_worked: string[]
  work_type_mix: Record<string, number>
  is_joint_venture: boolean
  jv_member_count: number
  data_confidence_score: number
}

export interface FinanceInfo {
  avg_npp: number
  avg_discount_pct: number
  win_rate: number
  total_bids: number
  health_score: number
  reliability_score: number
  completion_rate: number
  on_time_rate: number
  avg_delay_days: number
  estimated_liquidity_band_bdt: string
  work_type_mix: Record<string, number>
}

export interface TenderRecommendation {
  recommendation: 'BID' | 'CONSIDER' | 'RISKY_BID' | 'NO_BID'
  recommendation_score: number
  confidence_pct: number
  win_probability_estimate: number
  recommended_bid_amount: number
  factors: Record<string, number>
  risk_factors: string[]
  explanation: string
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
