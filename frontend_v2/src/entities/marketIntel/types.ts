/** Matches backend app/api/v2/market_intelligence.py */

export interface MarketOverviewStats {
  total_records: number
  agency_count: number
  contractor_count: number
  awarded_count: number
  total_awarded_bdt: number
  avg_award_bdt: number
  median_award_bdt: number
  median_nppi: number | null
  nppi_sample: number
}

export interface AwardHistoryYear {
  year: number
  award_count: number
  total_value_bdt: number
  avg_value_bdt: number
  contractor_count: number
  median_nppi: number | null
}

export interface AgencyBehaviour {
  agency_code: string
  award_count: number
  total_value_bdt: number
  avg_value_bdt: number
  median_value_bdt: number
  contractor_count: number
  median_nppi: number | null
  top_contractor: string | null
  top_wins: number | null
  contractor_concentration_pct: number | null
}

export interface ContractorStanding {
  contractor_name: string
  win_count: number
  total_value_bdt: number
  avg_value_bdt: number
  largest_award_bdt: number
  agency_count: number
  latest_award_year: number | null
  median_nppi: number | null
}

export interface NppiBucket {
  bucket: string
  count: number
}

export interface NppiAgency {
  agency_code: string
  sample_size: number
  median_nppi: number
}

export interface NppiAnalysis {
  summary: {
    sample_size: number
    p10: number
    p25: number
    median: number
    p75: number
    p90: number
  }
  distribution: NppiBucket[]
  by_agency: NppiAgency[]
}
