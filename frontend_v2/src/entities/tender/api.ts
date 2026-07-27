import { getAuthToken } from '../authToken'
import { authReady } from '../bootstrapAuth'
import type {
  TenderSearchParams,
  TenderSearchResult,
  TenderDetailResponse,
  TenderBrainDetail,
  TenderWorkspaceData,
  TenderWorkspaceUpdate,
  TenderProcessingResult,
} from './types'

const V1 = '/api'
const V2 = '/api/v2'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  await authReady()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, { headers, ...options })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}

/**
 * Tender search.
 *
 * Stays on /api/search/tenders: that endpoint searches an enriched view with
 * award amounts, winners and relevance ranking. The Phase 2 /api/v2/tenders
 * route is a plain CRUD list over the base table — it has no ranking and leaves
 * estimated_cost/award columns empty, so it is not a substitute for search.
 */
export function searchTenders(params: TenderSearchParams): Promise<TenderSearchResult> {
  const qs = new URLSearchParams()
  if (params.q) qs.set('q', params.q)
  if (params.agency) qs.set('agency', params.agency)
  if (params.limit != null) qs.set('limit', String(params.limit))
  if (params.offset != null) qs.set('offset', String(params.offset))
  if (params.scope) qs.set('scope', params.scope)
  return fetchJson<TenderSearchResult>(`${V1}/search/tenders?${qs.toString()}`)
}

/** Tender detail — documents + extracted variables. */
export function getTenderDetail(tenderId: string): Promise<TenderDetailResponse> {
  return fetchJson<TenderDetailResponse>(`${V1}/tender/${tenderId}`)
}

/** Enriched "brain" detail — optional, returns null when unavailable. */
export async function getTenderBrainDetail(tenderId: string): Promise<TenderBrainDetail | null> {
  try {
    const workspace = await getTenderWorkspace(tenderId)
    const overview = workspace.overview ?? {}
    return {
      tender: {
        tender_id: workspace.tender_id,
        title: String(overview.title ?? ''),
        agency: String(overview.agency ?? ''),
        zone: String(overview.zone ?? ''),
        procurement_method: String(overview.method ?? ''),
        pe_office: String(overview.procuring_entity ?? ''),
      },
      award: null,
    }
  } catch {
    return null
  }
}

/** Row shape returned by the Phase 2 CRUD endpoints. */
export interface TenderRecord {
  id: string
  tender_id: string
  package_no: string | null
  title: string | null
  procuring_entity: string | null
  district: string | null
  division: string | null
  estimated_cost: number | null
  closing_date: string | null
  opening_date: string | null
  status: string | null
  zone: string | null
  source: string | null
  created_at: string
  updated_at: string
}

/** Phase 2: fetch a single tender record (CRUD view, not the search view). */
export function getTenderRecord(tenderId: string): Promise<TenderRecord> {
  return fetchJson<TenderRecord>(`${V2}/tenders/${tenderId}`)
}

/** Phase 2: update editable tender fields. */
export function updateTender(
  tenderId: string,
  data: Partial<Pick<TenderRecord, 'title' | 'status' | 'estimated_cost' | 'closing_date'>>,
): Promise<TenderRecord> {
  return fetchJson<TenderRecord>(`${V2}/tenders/${tenderId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function getTenderWorkspace(tenderId: string): Promise<TenderWorkspaceData> {
  return fetchJson<TenderWorkspaceData>(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}`)
}

export function updateTenderWorkspace(
  tenderId: string,
  update: TenderWorkspaceUpdate,
): Promise<{ success: boolean; state: TenderWorkspaceUpdate }> {
  return fetchJson(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}`, {
    method: 'PATCH',
    body: JSON.stringify(update),
  })
}

export function snapshotEligibilityMatrix(tenderId: string) {
  return fetchJson(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/eligibility-matrix/snapshot`, { method: 'POST' })
}

export function refreshTenderEstimate(tenderId: string) {
  return fetchJson<any>(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/resolve-estimate?allow_live=true`, {
    method: 'POST',
  })
}

export function approveTenderEstimate(tenderId: string, candidate: Record<string, any>) {
  return fetchJson<any>(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/resolve-estimate/approve`, {
    method: 'POST',
    body: JSON.stringify({
      amount_bdt: candidate.amount_bdt,
      source_record_id: candidate.source_record_id,
      package_no: candidate.package_no,
      rationale: `Approved ${candidate.match_method || 'APP'} candidate at ${Math.round(Number(candidate.confidence || 0) * 100)}% confidence`,
    }),
  })
}

export function scanTenderChanges(tenderId: string) {
  return fetchJson<any>(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/watch/scan`, { method: 'POST' })
}

export function setTenderStageApproval(tenderId: string, stage: string, status: 'approved' | 'revoked') {
  return fetchJson(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/approvals`, {
    method: 'POST', body: JSON.stringify({ stage, status }),
  })
}

export function getUnmatchedBoqSuggestions(tenderId: string) {
  return fetchJson<any>(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/boq/unmatched-suggestions`)
}

export function resolveUnmatchedBoqItem(tenderId: string, input: { item_id: string; sor_code: string; agency: string; zone: string }) {
  return fetchJson(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/boq/resolve`, {
    method: 'POST', body: JSON.stringify(input),
  })
}

export async function processLiveTender(
  tenderId: string,
  options: { sorAgency?: string; zone?: string; fullPipeline?: boolean } = {},
): Promise<TenderProcessingResult> {
  const query = new URLSearchParams({
    sor_agency: options.sorAgency ?? 'BWDB',
    run_live_acquisition: 'true',
    full_pipeline: String(options.fullPipeline ?? false),
  })
  if (options.zone) query.set('zone', options.zone)
  const result = await fetchJson<TenderProcessingResult>(
    `${V1}/tender/${encodeURIComponent(tenderId)}/process-with-agents?${query}`,
    { method: 'POST' },
  )
  await fetchJson(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/resolve-estimate?allow_live=true`, {
    method: 'POST',
  })
  return result
}

export async function downloadTenderArtifact(url: string, filename: string): Promise<void> {
  await authReady()
  const token = getAuthToken()
  const response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!response.ok) throw new Error(`Artifact download failed with HTTP ${response.status}`)
  const href = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = href
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(href)
}

export async function openTenderEvidenceDocument(url: string, pageNumber?: number | null): Promise<void> {
  await authReady()
  const token = getAuthToken()
  const response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!response.ok) throw new Error(`Evidence document failed with HTTP ${response.status}`)
  const objectUrl = URL.createObjectURL(await response.blob())
  const target = `${objectUrl}${pageNumber ? `#page=${pageNumber}&zoom=page-width` : ''}`
  const opened = window.open(target, '_blank', 'noopener,noreferrer')
  if (!opened) {
    URL.revokeObjectURL(objectUrl)
    throw new Error('Allow pop-ups to open the evidence document')
  }
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 300_000)
}

export function completeTenderBoqRates(
  tenderId: string,
  input: { sor_agency: 'BWDB' | 'LGED' | 'PWD'; zone: string | null },
): Promise<{
  success: boolean
  comparison_id: string
  total_items: number
  matched_items: number
  unmatched_items: number
  export_url: string | null
}> {
  return fetchJson(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/boq-complete`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function recheckTenderDataQuality(tenderId: string): Promise<{
  success: boolean
  tender_id: string
  quality: TenderWorkspaceData['data_quality']
}> {
  return fetchJson(`${V1}/tender/${encodeURIComponent(tenderId)}/data-quality/recheck`, {
    method: 'POST',
  })
}

export function generateProfitMarginWorkbook(
  tenderId: string,
  input: {
    direct_cost_bdt: number
    overhead_pct: number
    tax_vat_pct: number
    contingency_pct: number
    target_profit_pct: number
  },
): Promise<{
  success: boolean
  recommended_bid_bdt: number
  profit_bdt: number
  effective_margin_pct: number
  artifact: { name: string; download_url: string }
}> {
  return fetchJson(`${V1}/tender-workspace/${encodeURIComponent(tenderId)}/profit-margin-workbook`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
