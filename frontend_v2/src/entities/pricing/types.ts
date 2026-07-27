export interface PricingPrediction {
  discount_percent: number
  bid_price: number
  cost: number
  sor_baseline: number
  margin_percent: number
  win_probability: number
  expected_profit: number
  confidence: number
  reasoning: string
  peer_bid_distribution: {
    mean: number
    std_dev: number
    percentile_at_your_bid: number
  }
}

export interface PricingHistory {
  discount_percent: number
  bid_price: number
  won: boolean
  date: string
  tender_id: string
}

export interface PricingScenario {
  name: string
  description: string
  discount_percent: number
  win_probability: number
  margin_percent: number
  expected_profit: number
}

export interface PricingStrategy {
  id: string
  tender_id: string
  company_id: string
  discount_percent: number
  bid_price: number
  expected_profit: number
  win_probability_predicted: number
  rationale: string
  risk_flags: string[]
  created_by: string
  created_at: string
}

export interface PricingAdvancedSettings {
  assumed_competitor_count?: number
  competitor_bidding_strategy?: 'rational' | 'aggressive' | 'conservative'
  fixed_cost_override?: number
  contingency_percent?: number
  risk_tolerance?: 'conservative' | 'balanced' | 'aggressive'
  min_acceptable_margin?: number
  max_acceptable_discount?: number
}
