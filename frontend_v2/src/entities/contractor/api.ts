import { fetchJson } from '../sharedApi'
import type { ContractorProfile, ContractorAwardPaginated } from './types'

/**
 * Two different backend prefixes are in play here (verified against the live
 * FastAPI route table):
 *   /api/v2/contractor/{company_id}/profile      <- profile only
 *   /api/contractors/{company_id}/{awards|eligibility|experience|opportunities|risk}
 * Everything below previously used the v2 prefix for all six, so the five
 * non-profile calls 404'd.
 */
const PROFILE_BASE = '/api/v2/contractor'
const BASE = '/api/contractors'

export function getContractorProfile(companyId: string): Promise<ContractorProfile> {
  return fetchJson<ContractorProfile>(`${PROFILE_BASE}/${companyId}/profile`, true)
}

export function getContractorExperience(companyId: string): Promise<ContractorProfile['experience']> {
  return fetchJson<ContractorProfile['experience']>(`${BASE}/${companyId}/experience`, true)
}

export function getContractorAwards(companyId: string, params?: { page?: number; page_size?: number }): Promise<ContractorAwardPaginated> {
  const qs = new URLSearchParams()
  if (params?.page != null) qs.set('page', String(params.page))
  if (params?.page_size != null) qs.set('page_size', String(params.page_size))
  const query = qs.toString()
  return fetchJson<ContractorAwardPaginated>(`${BASE}/${companyId}/awards${query ? `?${query}` : ''}`, true)
}

export function getContractorEligibility(companyId: string): Promise<ContractorProfile['eligibility']> {
  return fetchJson(`${BASE}/${companyId}/eligibility`, true)
}

export function getContractorRisk(companyId: string): Promise<ContractorProfile['risk_profile']> {
  return fetchJson(`${BASE}/${companyId}/risk`, true)
}

export function getContractorOpportunities(companyId: string): Promise<ContractorProfile['next_opportunities']> {
  return fetchJson(`${BASE}/${companyId}/opportunities`, true)
}
