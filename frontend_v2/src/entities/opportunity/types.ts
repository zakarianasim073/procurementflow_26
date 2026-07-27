export interface AgentResultItem {
  run_id: string
  source: string
  timestamp: string
  tender_id: string | null
  agent_id: string
  agent_name: string
  status: string
  execution_time_ms: number
  error?: string
  output?: Record<string, unknown>
}

export interface AgentResultsResponse {
  success: boolean
  total: number
  results: AgentResultItem[]
}

export interface AgencyItem {
  id: string
  name: string
  total_rates: number
  has_csv: boolean
}

export interface AgenciesResponse {
  success: boolean
  agencies: AgencyItem[]
}

export interface CrawlerStatusResponse {
  success: boolean
  running: boolean
  last_run: string | null
  queue: {
    pending: number
    processing: number
    completed: number
  }
}

export interface OpeningReportItem {
  id: string
  tender_id: string
  opening_date: string
  pe_office: string
  agency: string
  zone: string
  winner_name: string | null
  winner_amount: number | null
  has_slt: boolean
  has_alt: boolean
  bidders_count: number
}

export interface OpeningReportsResponse {
  success: boolean
  total: number
  reports: OpeningReportItem[]
}
