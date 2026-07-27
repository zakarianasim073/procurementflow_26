import { fetchJson } from '../sharedApi'
import type { CapacityInfo, FinanceInfo, TenderRecommendation, TDSCriteria } from './types'

// Phase 3: Migration Status
// Current: v1 endpoints (/api/v1/contractors/*, /api/v1/qualification/*)
// Target: /api/v2/qualification/* when backend v2 is available
// Migration guide: PHASE_3_V1_TO_V2_MIGRATIONS.md

const BASE = '/api'

export async function getContractorCapacity(contractorId: string, tenderValueBdt?: number): Promise<CapacityInfo | null> {
  try {
    const qs = tenderValueBdt ? `?tender_value_bdt=${tenderValueBdt}` : ''
    return await fetchJson<CapacityInfo>(`${BASE}/v1/contractors/${contractorId}/capacity${qs}`, true)
  } catch {
    return null
  }
}

export async function getContractorFinance(contractorId: string): Promise<FinanceInfo | null> {
  try {
    return await fetchJson<FinanceInfo>(`${BASE}/v1/contractors/${contractorId}/finance`, true)
  } catch {
    return null
  }
}

export async function getTenderRecommendation(tenderId: string, contractorId: string): Promise<TenderRecommendation | null> {
  try {
    return await fetchJson<TenderRecommendation>(`${BASE}/v1/tender/${tenderId}/recommend/${contractorId}`, true)
  } catch {
    return null
  }
}

function requirementNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value !== 'string') return null
  const match = value.replace(/,/g, '').match(/[\d.]+/)
  if (!match) return null
  const amount = Number(match[0])
  if (!Number.isFinite(amount)) return null
  const normalized = value.toLowerCase()
  if (normalized.includes('crore')) return amount * 10_000_000
  if (normalized.includes('lakh')) return amount * 100_000
  return amount
}

export async function getTenderTDSCriteria(tenderId: string): Promise<TDSCriteria | null> {
  try {
    const data = await fetchJson<{ requirements: Array<{ key: string; value: unknown }> }>(
      `${BASE}/tender-workspace/${encodeURIComponent(tenderId)}`,
      true,
    )
    const values = Object.fromEntries(data.requirements.map(item => [item.key, item.value]))
    if (!Object.keys(values).length) return null
    return {
      general_experience: values.general_experience == null ? null : String(values.general_experience),
      specific_experience_value: requirementNumber(values.specific_experience_value),
      specific_experience_count: requirementNumber(values.specific_experience_count),
      avg_annual_turnover: requirementNumber(values.avg_annual_turnover),
      liquid_assets: requirementNumber(values.liquid_assets),
      min_tender_capacity: requirementNumber(values.min_tender_capacity),
      tender_security: requirementNumber(values.tender_security),
      performance_security: requirementNumber(values.performance_security),
      retention_money: requirementNumber(values.retention_money),
    }
  } catch {
    return null
  }
}
