import type { ReactNode } from 'react'

export interface KpiStripProps {
  children: ReactNode
}

/**
 * Generic horizontal-scroll container for KPI cards, used as ScreenTemplate's `kpiStrip` slot content.
 * Individual KPI cards (RevenueKpi, PipelineKpi, ...) are business components built in PFX-11 —
 * this is just the structural row they sit in.
 */
export function KpiStrip({ children }: KpiStripProps) {
  return <div className="flex gap-4 overflow-x-auto pb-1">{children}</div>
}
