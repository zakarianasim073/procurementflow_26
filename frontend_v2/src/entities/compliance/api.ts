import { fetchJson } from '@entities/sharedApi'
import type { ComplianceCheck, TDSCriteria } from './types'

const V1 = '/api'

export interface ValidationFinding {
  type: string
  severity: string
  message: string
  item_no?: string
}

export function getComplianceCheck(tenderId: string): Promise<ComplianceCheck | null> {
  return fetchJson<ComplianceCheck | null>(`${V1}/validation/tender/${tenderId}`)
}

export function getTdsCriteria(tenderId: string): Promise<TDSCriteria | null> {
  return fetchJson<TDSCriteria | null>(`${V1}/brain/query`, {
    method: 'POST',
    body: JSON.stringify({ entry_type: 'tds_text', tender_id: tenderId }),
  })
}

export function runComplianceCheck(tenderId: string): Promise<ComplianceCheck> {
  return fetchJson<ComplianceCheck>(`${V1}/validation/tender/${tenderId}`)
}

export function validatePayload(payload: {
  tender_id: string
  items: Array<{ item_no: string; description: string; unit: string; quantity: number; rate: number }>
  required_documents?: string[]
  provided_documents?: string[]
}): Promise<ComplianceCheck> {
  return fetchJson<ComplianceCheck>(`${V1}/validation/check`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
