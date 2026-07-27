import { fetchJson } from '@entities/sharedApi'
import type { BoqComparisonResult, BoqUploadResponse, BoqJobStatus } from './types'

const V1 = '/api'

export function uploadBoq(file: File): Promise<BoqUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return fetchJson<BoqUploadResponse>(`${V1}/boq/upload`, { method: 'POST', body: formData, headers: {} })
}

export function compareBoq(boqFileId: string, sorAgency: string, zone?: string, tenderInfo?: string): Promise<{ job_id: string; status: string; status_url: string }> {
  const formData = new FormData()
  formData.append('boq_file_id', boqFileId)
  formData.append('sor_agency', sorAgency)
  if (zone) formData.append('zone', zone)
  if (tenderInfo) formData.append('tender_info', tenderInfo)
  return fetchJson(`${V1}/boq/compare`, { method: 'POST', body: formData, headers: {} })
}

export function brainCompare(tenderId: string, sorAgency: string, zone?: string): Promise<{ job_id: string; status: string; status_url: string }> {
  const formData = new FormData()
  formData.append('tender_id', tenderId)
  formData.append('sor_agency', sorAgency)
  if (zone) formData.append('zone', zone)
  return fetchJson(`${V1}/boq/brain-compare`, { method: 'POST', body: formData, headers: {} })
}

export function getBoqJobStatus(jobId: string): Promise<BoqJobStatus> {
  return fetchJson<BoqJobStatus>(`${V1}/boq/jobs/${jobId}`)
}

export function getBoqJobResult(jobId: string): Promise<BoqComparisonResult> {
  return fetchJson<BoqComparisonResult>(`${V1}/boq/jobs/${jobId}/result`)
}

export function getBoqLatest(): Promise<BoqComparisonResult | null> {
  return fetchJson<BoqComparisonResult | null>(`${V1}/boq/latest`)
}

export function getBoqHistory(skip = 0, limit = 20): Promise<BoqComparisonResult[]> {
  return fetchJson<BoqComparisonResult[]>(`${V1}/boq/history?skip=${skip}&limit=${limit}`)
}

export function getBoqComparison(comparisonId: string): Promise<BoqComparisonResult> {
  return fetchJson<BoqComparisonResult>(`${V1}/boq/${comparisonId}`)
}
