import { getAuthToken } from '../authToken'
import { authReady } from '../bootstrapAuth'
import type {
  DocumentListParams,
  DocumentMetadata,
  DocumentExtractionResponse,
} from './types'

const BASE = '/api/v2/documents'

function authHeaders(json = true): Record<string, string> {
  const headers: Record<string, string> = {}
  if (json) headers['Content-Type'] = 'application/json'
  const token = getAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  await authReady()
  const res = await fetch(url, { headers: authHeaders(), ...options })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}

/** GET /api/v2/documents — returns a bare array */
export function listDocuments(params: DocumentListParams): Promise<DocumentMetadata[]> {
  const qs = new URLSearchParams()
  if (params.tender_id) qs.set('tender_id', params.tender_id)
  if (params.doc_type) qs.set('doc_type', params.doc_type)
  if (params.skip != null) qs.set('skip', String(params.skip))
  if (params.limit != null) qs.set('limit', String(params.limit))

  return fetchJson<DocumentMetadata[]>(`${BASE}?${qs.toString()}`)
}

export function getDocument(documentId: string): Promise<DocumentMetadata> {
  return fetchJson<DocumentMetadata>(`${BASE}/${documentId}`)
}

/** POST /api/v2/documents/upload — tender_id and doc_type are form fields */
export async function uploadDocument(
  tenderId: string,
  file: File,
  docType: string,
): Promise<DocumentMetadata> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('tender_id', tenderId)
  formData.append('doc_type', docType)

  await authReady()
  const res = await fetch(`${BASE}/upload`, {
    method: 'POST',
    headers: authHeaders(false),
    body: formData,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}

export function extractDocument(documentId: string): Promise<DocumentExtractionResponse> {
  return fetchJson<DocumentExtractionResponse>(`${BASE}/${documentId}/extract`, {
    method: 'POST',
  })
}

export function deleteDocument(documentId: string): Promise<void> {
  return fetchJson<void>(`${BASE}/${documentId}`, { method: 'DELETE' })
}
