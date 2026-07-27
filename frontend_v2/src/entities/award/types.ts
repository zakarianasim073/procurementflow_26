// Award model - Match frontend expectations after backend updates

export interface Award {
  // Frontend expects these exact field names
  id: string
  source: string
  source_id: string
  
  // Frontend-expected new fields from backend
  tender_id?: string                    // From backend Award.tender_id
  award_date?: string                   // From backend Award.award_date
  award_notice_no?: string             // From backend Award.award_notice_no
  awarding_agency?: string             // From backend Award.awarding_agency (renamed from procuring_entity)
  
  // Backend fields mapped to frontend expectations
  procuring_entity: string             // Backend field - frontend expects award_agency (but we'll keep procuring_entity for compatibility)
  entity_type?: string
  ministry?: string
  work_name: string                    // Backend field - frontend expects tender_title
  work_type?: string                    // Frontend expects: work_type
  district?: string                     // Frontend expects: district
  division?: string                     // Frontend expects: division
  
  // Award data
  estimated_cost?: number
  awarded_amount?: number
  currency: string
  contractor_name: string
  contractor_license?: string
  contractor_address?: string
  contract_period_days?: number
  work_start_date?: string
  work_completion_date?: string
  
  // Legacy data
  raw_data?: Record<string, unknown>
  boq_items?: Record<string, unknown>
  discount_pct?: number
  unit_rates?: Record<string, unknown>
  
  // Metadata
  created_at?: string
  updated_at?: string
}

export interface AwardStats {
  // Frontend expects these exact fields
  total_awards: number                  // Total number of awards
  total_awarded_amount: number          // Total amount awarded (BDT)
  avg_variance_pct: number               // Average variance percentage (from backend calculation)
  avg_discount_pct?: number              // Alias for avg_variance_pct (frontend uses this name)
  awards_by_agency: {                     // Frontend expects: awards_by_agency
    name: string
    count: number
    total_amount: number
  }[]
  
  // Backend has top_entities and top_contractors - keep for backwards compatibility
  top_entities?: {                       // Keep backend data for compatibility
    name: string
    count: number
    total_amount: number
  }[]
  top_contractors?: {                    // Keep backend data for compatibility
    name: string
    count: number
    total_amount: number
  }[]
}
