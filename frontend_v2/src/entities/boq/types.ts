export interface BoqItem {
  item_no?: string
  code?: string
  agency?: string
  work_type?: string
  desc: string
  unit: string
  qty: number
  rate?: number
  sor_rate?: number
  diff?: number
  pct_diff?: number
  flag?: string
  section?: string
  sor_source?: string
}

export interface BoqSummary {
  by_work_type: any[]
  total_sor: number
  total_quoted: number
  discount_pct: number
  total_items: number
  matched_items: number
  variance_items: number
  mismatched_items: number
}

export interface BoqComparisonResult {
  success: boolean
  comparison_id?: string
  boq_file_id?: string
  sor_agency?: string
  zone?: string
  items: BoqItem[]  // ✅ FRONTEND EXPECTS: "items" (BACKEND API SHOULD RETURN THIS)
  summary: BoqSummary
  flagged?: any[]
  total_items?: number
  mismatches?: number
  variances?: number
  matches?: number
  below_sor?: number
  excel_path?: string
  docx_path?: string
  tenderai_dir?: string
  created_at?: string
  financial_check?: any[]
  estimated_cost_app?: number
}

export interface BoqUploadResponse {
  success: boolean
  boq_file_id?: string
  file_id?: string
  filename: string
  item_count?: number
  file_type?: string
  size_bytes?: number
  status: string
  object_key?: string
}

export interface BoqJobStatus {
  job_id: string
  kind: string
  status: string
  progress: number | null
  error: string | null
  comparison_id: string | null
  result_url: string | null
  created_at: string
  updated_at: string
}
