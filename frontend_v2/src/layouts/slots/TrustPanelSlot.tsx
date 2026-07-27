import type { ReactNode } from 'react'

export interface TrustPanelSlotProps {
  children: ReactNode
}

/**
 * Structural wrapper for ScreenTemplate's `trustPanel` slot. Per ADR-002, anything rendered
 * here should ultimately be a RecommendationCard/TrustPanel from PFX-09 — this wrapper only
 * supplies the consistent card chrome (border, padding, heading) so every workspace's trust
 * panel looks the same regardless of what AI output it's showing.
 */
export function TrustPanelSlot({ children }: TrustPanelSlotProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      {/* gray-500, not gray-400: PFX-06's contrast audit found gray-400-on-white fails AA (2.54:1) */}
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Trust &amp; Evidence</p>
      {children}
    </div>
  )
}
