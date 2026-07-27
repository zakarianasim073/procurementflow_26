export interface FeedbackEntry {
  id: string
  tender_id: string
  bid_decision: string
  bid_price: number
  actual_price: number | null
  award_status: string
  helpfulness_score: number
  feature_tags: string[]
  notes: string | null
  created_at: string
  updated_at: string
}

export interface FeedbackStats {
  total_submitted: number
  total_awaiting: number
  total_resolved: number
  resolution_rate: number
  resolution_rate_change: number | null
  bid_rate: number
  win_rate: number
  total_tenders_recommended: number
  bids_placed: number
  won_tenders: number
}

export interface FeedbackAwaitingItem {
  tender_id: string
  agency: string
  bid_deadline: string
  award_expected_date: string
}

export interface FeedbackSubmitResult {
  id: string
  created_at: string
}

export interface FeedbackSubmitPayload {
  tender_id: string
  bid_decision: string
  bid_price: number
  actual_price?: number
  award_status: string
  helpfulness_score: number
  feature_tags?: string[]
  notes?: string
}
