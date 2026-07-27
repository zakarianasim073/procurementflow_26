export interface TenderSearchParams {
  q?: string
  agency?: string
  limit?: number
  offset?: number
  scope?: 'live' | 'all'
}

export interface TenderItem {
  package_no: string
  tender_id: string
  agency_code: string
  zone_name: string
  title: string
  estimated_cost_bdt: number
  award_amount_bdt: number | null
  winner: string | null
  award_date: string | null
  rank: number
  closing_date?: string | null
  source?: 'egp_live' | string
  tender_security_amount_bdt?: number | null
  tender_security_text?: string | null
}

export interface TenderSearchResult {
  success: boolean
  query: string
  entity_type: string
  limit: number
  offset: number
  has_more: boolean
  next_offset: number | null
  data: TenderItem[]
  count: number
}

// ── Tender Detail ──────────────────────────────────────────────────────

export interface TenderDetailResponse {
  success: boolean
  tender_id: string
  documents: Record<string, string>
  variables: Record<string, unknown>
}

export interface TenderBrainAward {
  contractor_name: string
  award_amount: number
}

export interface TenderBrainDetail {
  tender: {
    tender_id: string
    title: string
    agency: string
    zone: string
    procurement_method: string
    pe_office: string
  }
  award: TenderBrainAward | null
}

export interface TenderWorkspaceData {
  tender_id: string
  overview: Record<string, any>
  progress: {
    completion_pct: number
    readiness_score: number
    compliance_score: number
    missing_tasks: string[]
    critical_blockers: string[]
    countdown_seconds: number | null
    next_action: string
  }
  documents: Array<{ type: string; name: string; path: string }>
  requirements: Array<{
    key: string
    label: string
    value: unknown
    source: string
    status: string
    evidence: {
      document_type: string
      page_number: number | null
      clause_text: string | null
      highlight_text: string
      match_method: string
      source_entry_type: string
      knowledge_entry_id: string | null
      document_url: string | null
    }
  }>
  eligibility: {
    score: number
    recommendation: string
    explanation: string
    checks: Array<Record<string, any>>
    matrix: Array<Record<string, any>>
    contractor_id?: string | null
    company_documents_considered?: number
  }
  document_checklist: Array<{ name: string; status: string; required: boolean }>
  forms: Array<{ name: string; status: string }>
  boq: Record<string, any>
  rate_analysis: Record<string, any>
  pricing: Record<string, any>
  compliance: { score: number; requirements_linked: number; violations: string[] }
  validation: Array<{ name: string; passed: boolean }>
  data_quality: {
    status: 'not_checked' | 'passed' | 'warning' | 'blocked'
    score: number
    agent_use_allowed: boolean
    critical_count: number
    warning_count: number
    checked_at?: string
    issues: Array<{ code: string; severity: 'critical' | 'warning'; message: string; evidence: Record<string, any> }>
  }
  risks: Array<{ category: string; level: string; issue: string; mitigation: string }>
  collaboration: {
    tasks: Array<Record<string, any>>
    comments: Array<Record<string, any>>
    approvals: Array<Record<string, any>>
    activity: Array<Record<string, any>>
    approval_stages: Array<{ stage: string; status: string }>
  }
  submission: Record<string, any>
  enterprise: Record<string, any>
  agent_runs: Array<{
    run_id: string
    agent_id: string
    agent_name: string
    status: string
    error: string | null
    output: Record<string, unknown>
    execution_time_ms: number
    timestamp: string | null
  }>
  outputs: {
    runtime_summary: string | null
    pipeline_result: Record<string, unknown>
    artifacts: Array<{
      name: string
      kind: string
      size_bytes: number
      sha256: string
      download_url: string
    }>
  }
}

export interface TenderWorkspaceUpdate {
  tasks?: Array<Record<string, any>>
  document_statuses?: Record<string, string>
  form_statuses?: Record<string, string>
  approvals?: Array<Record<string, any>>
  comments?: Array<Record<string, any>>
  owner?: string
  boq_completion?: number
  contractor_id?: string
}

export interface TenderProcessingResult {
  success: boolean
  tender_id: string
  quality_gate: TenderWorkspaceData['data_quality']
  pipeline_result: Record<string, any>
  documents: Record<string, any> | null
  agent_outputs: Record<string, any>
  artifacts: Array<Record<string, any>>
}
