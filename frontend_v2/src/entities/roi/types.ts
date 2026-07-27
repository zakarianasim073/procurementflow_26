export interface HoursSavedBreakdown {
  research: number
  bid_prep: number
  compliance_check: number
}

export interface PartnerValueMetrics {
  company_id: string
  company_name: string
  active_users: number
  tenders_analyzed: number
  bids_placed_with_pf: number
  hours_saved: {
    total: number
    per_tender: number
    breakdown: HoursSavedBreakdown
  }
  compliance_improvements: {
    tenders_analyzed_for_compliance: number
    issues_detected_by_pf: number
    issues_avoided: number
    compliance_score_pre: number
    compliance_score_post: number
  }
  win_rate: {
    post_adoption: number
    tenders_won_with_pf: number
    tenders_lost_with_pf: number
  }
  pricing_accuracy: {
    ai_price_matches: number
    ai_price_avg_delta_percent: number
    user_followed_ai_price: number
  }
  user_adoption_curve: Array<{ week: string; active_users: number }>
  edf_feedback_rate: number
  edf_helpfulness_score: number
}

export interface ExecutiveRoiReport {
  period: 'month' | 'quarter' | 'year'
  date_range: { start: string; end: string }
  aggregate: {
    total_partners: number
    total_hours_saved: number
    total_contracts_analyzed: number
    total_win_rate_improvement: number
    compliance_issues_prevented: number
    estimated_value_created: number
  }
  partner_rankings: PartnerValueMetrics[]
  adoption_momentum: 'accelerating' | 'steady' | 'declining'
  feature_adoption: {
    pricing_panel_usage: number
    competitor_intel_usage: number
    compliance_check_usage: number
  }
}
