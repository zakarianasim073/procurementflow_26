import type { ReactNode } from 'react'

export interface ActivityTimelineSlotProps {
  children: ReactNode
}

/**
 * Structural wrapper for ScreenTemplate's `activityTimeline` slot. Holds the consistent
 * card chrome for a recent-activity/audit-trail list; the actual entries (evidence updates,
 * status changes, agent runs) are supplied per-feature by later tickets.
 */
export function ActivityTimelineSlot({ children }: ActivityTimelineSlotProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      {/* gray-500, not gray-400: PFX-06's contrast audit found gray-400-on-white fails AA (2.54:1) */}
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Activity</p>
      <ol className="space-y-3">{children}</ol>
    </div>
  )
}
