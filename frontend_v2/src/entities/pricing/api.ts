import { fetchJson } from '../sharedApi'
import type { PricingPrediction, PricingHistory, PricingStrategy } from './types'

const BASE = '/api/v2/tender'

export interface PricingPredictionParams {
  /** Required by the backend. */
  bid_price: number
  /** Required by the backend. */
  estimated_cost: number
  /** Required by the backend. */
  bidder_count: number
  agency?: string
  zone?: string
  /** Sent for the caller's own bookkeeping; the backend ignores it. */
  discount?: number
}

/**
 * GET /api/v2/tender/{tender_id}/pricing-lab/prediction
 * Required query params (per the live OpenAPI spec):
 *   bid_price, estimated_cost, bidder_count   (agency, zone optional)
 * This used to send only `discount`, so every call returned 422.
 */
export function getPricingPrediction(
  tenderId: string,
  params: PricingPredictionParams,
): Promise<PricingPrediction> {
  const qs = new URLSearchParams({
    bid_price: String(params.bid_price),
    estimated_cost: String(params.estimated_cost),
    bidder_count: String(params.bidder_count),
  })
  if (params.agency) qs.set('agency', params.agency)
  if (params.zone) qs.set('zone', params.zone)
  if (params.discount != null) qs.set('discount', String(params.discount))
  return fetchJson<PricingPrediction>(`${BASE}/${tenderId}/pricing-lab/prediction?${qs}`, true)
}

/**
 * GET /api/v2/tender/{tender_id}/pricing-lab/history.
 * Returns historical bid/pricing data from award_records_v2 for comparable analysis.
 */
export function getPricingHistory(tenderId: string): Promise<PricingHistory[]> {
  return fetchJson<PricingHistory[]>(`${BASE}/${tenderId}/pricing-lab/history`, true)
}

/**
 * POST /api/v2/tender/{tender_id}/pricing-strategy.
 * Saves a named pricing strategy for the tender.
 */
export function savePricingStrategy(
  tenderId: string,
  strategy: { name: string; discount_percent: number; bid_price: number; rationale: string },
): Promise<PricingStrategy> {
  return fetchJson<PricingStrategy>(`${BASE}/${tenderId}/pricing-strategy`, {
    method: 'POST',
    body: JSON.stringify(strategy),
    authed: true,
  })
}

/**
 * GET /api/v2/tender/{tender_id}/pricing-strategy/{strategy_id}.
 * Retrieves a saved pricing strategy by ID.
 */
export function getPricingStrategy(tenderId: string, strategyId: string): Promise<PricingStrategy> {
  return fetchJson<PricingStrategy>(`${BASE}/${tenderId}/pricing-strategy/${strategyId}`, true)
}
