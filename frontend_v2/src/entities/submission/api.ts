import { fetchJson } from '@entities/sharedApi'
import type { Submission, SubmissionTimeline } from './types'

const V1 = '/api/v1'

interface BackendTenderSummary {
  tender_id: string
  title?: string
  procuring_entity?: string
  documents?: Record<string, unknown>
}

interface BackendTenderList {
  tenders: BackendTenderSummary[]
}

interface BackendGeneratedDocuments {
  tender_id: string
  generated: Array<{ filename: string; size_kb?: number }>
}

interface BackendDbTender {
  id: string
  tender_id: string
  title: string
  procuring_entity?: string
  status?: Submission['status']
  closing_date?: string
  created_at?: string
  updated_at?: string
}

function toSubmission(tender: BackendTenderSummary): Submission {
  const documents = Object.entries(tender.documents ?? {}).map(([name, value], index) => ({
    document_id: `${tender.tender_id}-${index}`,
    name,
    type: typeof value === 'object' && value && 'type' in value ? String(value.type) : 'tender_document',
    uploaded_at: '',
    size: 0,
  }))

  return {
    submission_id: tender.tender_id,
    tender_id: tender.tender_id,
    tender_title: tender.title || `Tender ${tender.tender_id}`,
    agency: tender.procuring_entity || 'Unknown agency',
    status: documents.length ? 'preparing' : 'draft',
    deadline: '',
    documents,
    created_at: '',
    updated_at: '',
  }
}

export async function getSubmissions(tenderId?: string): Promise<Submission[]> {
  if (tenderId) {
    const detail = await fetchJson<BackendTenderSummary>(`${V1}/tender/${encodeURIComponent(tenderId)}`, true)
    return [toSubmission({ ...detail, tender_id: detail.tender_id || tenderId })]
  }
  const data = await fetchJson<BackendTenderList>(`${V1}/tender/list`, true)
  return (data.tenders ?? []).map(toSubmission)
}

export async function getSubmission(tenderId: string): Promise<Submission> {
  const [submission] = await getSubmissions(tenderId)
  return submission
}

export async function getSubmissionTimeline(tenderId: string): Promise<SubmissionTimeline> {
  const data = await fetchJson<BackendGeneratedDocuments>(
    `${V1}/tender-docs/${encodeURIComponent(tenderId)}/list`,
    true,
  )
  return {
    submission_id: tenderId,
    events: (data.generated ?? []).map((document, index) => ({
      event_id: `${tenderId}-${index}`,
      action: `Generated ${document.filename}`,
      user: 'ProcureFlow',
      timestamp: '',
      details: document.size_kb == null ? undefined : `${document.size_kb} KB`,
    })),
  }
}

export function generateSubmissionDocs(params: {
  tender_id: string
  contractor_id?: string
  bidder_name?: string
  bidder_address?: string
  sor_agency?: string
  zone?: string
}): Promise<{ success: boolean; tender_id: string; generated_count: number; generated_files: string[] }> {
  return fetchJson(`${V1}/tender-docs/generate`, {
    method: 'POST',
    body: JSON.stringify(params),
    authed: true,
  })
}

export function listSubmissionDocs(tenderId: string): Promise<{ success: boolean; tender_id: string; has_docs: boolean; generated: Array<{ filename: string; path: string; size_kb: number; download_url: string }> }> {
  return fetchJson(`${V1}/tender-docs/${tenderId}/list`, true)
}

export async function updateSubmissionStatus(tenderId: string, status: string): Promise<Submission> {
  const tender = await fetchJson<BackendDbTender>(`${V1}/tender/db/${tenderId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
    authed: true,
  })
  return {
    submission_id: tender.id,
    tender_id: tender.tender_id,
    tender_title: tender.title,
    agency: tender.procuring_entity || 'Unknown agency',
    status: tender.status ?? 'draft',
    deadline: tender.closing_date ?? '',
    documents: [],
    created_at: tender.created_at ?? '',
    updated_at: tender.updated_at ?? '',
  }
}
