// ── V1 Executive Overview ──────────────────────────────────────────

export interface ExecutiveOverview {
  slt: { total_evaluations: number; evaluations: unknown[] }
  agents: {
    total: number
    active: number
    by_phase: Record<string, number>
    phase_labels: Record<string, string>
  }
  bwdb: { tenders_scanned: number; bwdb_matches: number; alerts: unknown[]; alert_count: number }
  embedding: { knowledge_total: number; by_domain: Record<string, number> }
  pipeline: {
    phases: Array<{ phase: string; label: string; total: number; registered: number; agents: number; registered_agents: number }>
    total_agents_phased: number
  }
  predictions: { total_predictions: number; contractors_with_data: number }
  npp: { total_npp_records: number; by_agency: Record<string, number>; agencies_with_data: string[] }
  execution: {
    eexperience_completed: number
    ecms_ongoing: number
    eexperience_value_bdt: number
    ecms_value_bdt: number
  }
  timestamp: string
}

// ── V1 Executive Pipeline ──────────────────────────────────────────

export interface ExecutivePipeline {
  success: boolean
  total_live_tenders: number
  estimated_total_pipeline_value_bdt: number
  value_note: string
  agencies: Array<{
    agency_code: string
    live_tenders: number
    closing_7d: number
    closing_14d: number
    closing_30d: number
    avg_historical_award_bdt: number
    estimated_pipeline_value_bdt: number
  }>
}

export interface AgencyLiveTender {
  tender_id: string
  package_no: string
  work_name: string
  pe_name: string | null
  submission_last_date: string
  tender_security_amount_bdt: number | null
  tender_security_text: string | null
  app_estimated_amount_bdt: number | null
  estimate_source: 'app_records' | null
}

export interface AgencyLiveTenderResponse {
  success: boolean
  agency_code: string
  total: number
  limit: number
  offset: number
  tenders: AgencyLiveTender[]
}

export interface LiveEnrichmentQueueItem {
  id: string
  tender_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  priority_score: number
  agency_code: string | null
  package_no: string | null
  title: string | null
  closing_datetime: string | null
  app_estimated_amount_bdt: number | null
  estimate_source: string | null
  requirements_count: number
  tender_security_text: string | null
  quality_status: 'not_checked' | 'passed' | 'warning' | 'blocked'
  quality_score: number | null
  quality_critical_count: number
  quality_warning_count: number
  error: string | null
  queued_at: string | null
  started_at: string | null
  completed_at: string | null
  updated_at: string | null
}

export interface LiveEnrichmentQueueResponse {
  success: boolean
  counts: Record<string, number>
  items: LiveEnrichmentQueueItem[]
}

export interface BidShortlistItem extends LiveEnrichmentQueueItem {
  score: number
  decision: 'BID' | 'REVIEW' | 'NO-BID'
  district: string | null
  competition_count: number
  expected_margin_pct: number | null
  score_breakdown: Record<string, number>
}

export interface BidShortlistResponse {
  success: boolean
  profile: { id: string; display_name: string } | null
  profile_required: boolean
  scoring_mode: string
  items: BidShortlistItem[]
}

// ── V2 Analytics Market Overview ───────────────────────────────────

export interface MarketOverview {
  total_tenders: number
  total_value_bdt: number
  avg_value_bdt: number
  awarded_count: number
}

// ── V1 Executive Report ────────────────────────────────────────────

export interface ExecutiveReport {
  success: boolean
  report: {
    bid_suggestion: {
      decision: 'Bidding Recommended' | 'Marginal Value (Proceed with Caution)' | 'Do Not Bid'
      optimal_discount: string | null
      optimal_discount_breakdown: Record<string, number>
      recommended_quoted_amount: number | null
      strategy: string
    }
    win_prediction: {
      probability: string
      confidence: 'Low' | 'Medium' | 'High'
      factors: string[]
      model_probability: string
      model_trained: boolean
    }
    model_intelligence: {
      win_probability: string
      slt_risk: string
      confidence: string
      evidence: { score: number }
      factors: { win: string[]; slt: string[] }
    }
    slt_intelligence: {
      slt_risk: string
      slt_probability: string | null
      sd_value: number | null
      nppi: number | null
      oe_discount: number | null
    }
    boq_analysis: {
      compared: boolean
      items: number
      matches: number
      variances: number
      mismatches: number
      discount_pct: number | null
      boq_file_id: string | null
    }
    market_rate: {
      deviation_pct: string | null
      trend: string
      notes: string
    }
    procurement_head_decision: {
      summary: string
      action_items: string[]
    }
  }
}

// ── V2 Predictions Model Status ────────────────────────────────────

export interface PredictionsModelStatus {
  tender_price_model: {
    name: string
    version: string | null
    validation_rmse: number | null
    validation_r2: number | null
    training_samples: number
    trained_at: string | null
    deployed_at: string | null
  }
  bid_price_model: {
    name: string
    version: string | null
    validation_rmse: number | null
    validation_r2: number | null
    training_samples: number
    trained_at: string | null
    deployed_at: string | null
  }
}

// ── V2 Analytics Live Metrics ──────────────────────────────────────

export interface LiveMetrics {
  overview: MarketOverview
  top_agencies: Array<{
    agency_code: string
    agency_name: string
    tender_count: number
    total_value_bdt: number
    awarded_count: number
  }>
  top_contractors: Array<{
    contractor_id: string
    contractor_name: string
    total_bids: number
    won_bids: number
    win_rate_pct: number
    avg_bid_amount_bdt: number
    avg_award_value_bdt: number
    award_count: number
  }>
  latest_trend: {
    month: string
    tender_count: number
    total_value_bdt: number
  } | null
  warehouse: {
    dim_agencies: number
    dim_contractors: number
    fact_tenders: number
    fact_awards: number
    fact_bids: number
  }
  timestamp: string
}
