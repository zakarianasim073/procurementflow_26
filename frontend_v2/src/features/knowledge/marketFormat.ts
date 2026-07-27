/** Shared formatting for the market intelligence panels. */

/**
 * Compact BDT using the local scale: lakh crore above 1e12, crore above 1e7,
 * lakh above 1e5, plain taka below. Market-wide totals reach 2.4e12, which
 * reads as "242905.6Cr" without the top tier.
 */
export function bdt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value) || value <= 0) return '—'
  if (value >= 1e12) return `${(value / 1e12).toFixed(2)} Lakh Cr`
  if (value >= 1e7) return `${(value / 1e7).toFixed(1)}Cr`
  if (value >= 1e5) return `${(value / 1e5).toFixed(1)}L`
  return `৳${Math.round(value).toLocaleString()}`
}

export function count(value: number | null | undefined): string {
  return value == null ? '—' : value.toLocaleString()
}

/** NPPI as a percentage of the published estimate. */
export function nppiPct(ratio: number | null | undefined): string {
  if (ratio == null || !Number.isFinite(ratio)) return '—'
  return `${(ratio * 100).toFixed(1)}%`
}

/**
 * Colour an NPPI value by how far the award sat below the estimate.
 * Deeper discounts are the more competitive end of the market.
 */
export function nppiTone(ratio: number | null | undefined): string {
  if (ratio == null || !Number.isFinite(ratio)) return 'text-gray-400 dark:text-gray-600'
  if (ratio < 0.9) return 'text-emerald-600 dark:text-emerald-400'
  if (ratio < 0.98) return 'text-blue-600 dark:text-blue-400'
  if (ratio <= 1.02) return 'text-amber-600 dark:text-amber-500'
  return 'text-red-600 dark:text-red-400'
}
