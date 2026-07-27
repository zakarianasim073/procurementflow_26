import { useState, type ReactNode } from 'react'
import clsx from 'clsx'

export interface AiDockSlotProps {
  /** Icon/label for the collapsed FAB shown below 768px. */
  collapsedLabel?: string
  children: ReactNode
}

/**
 * Structural wrapper for ScreenTemplate's `aiDock` slot: an inline panel at >=768px,
 * a floating action button that expands into a sheet below that. The real AI Dock
 * content (PromptBox, StreamingResponse, ...) is built in PFX-21 — this component only
 * owns the collapse/expand shell so every screen gets identical Dock behavior for free.
 */
export function AiDockSlot({ collapsedLabel = 'AI Assistant', children }: AiDockSlotProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="md:contents">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className={clsx(
          // bg-interactive (solid brand-600), not bg-brand-gradient: PFX-06's contrast audit found
          // white text fails AA at every stop of the gradient (down to 3.46:1 at the fuchsia end).
          'md:hidden rounded-full bg-interactive px-4 py-3 text-sm font-semibold text-white shadow-lg',
        )}
      >
        {collapsedLabel}
      </button>
      <div
        className={clsx(
          'md:block',
          expanded
            ? 'fixed inset-x-4 bottom-20 top-20 z-50 overflow-y-auto rounded-xl bg-white p-4 shadow-2xl dark:bg-gray-900'
            : 'hidden'
        )}
      >
        {children}
      </div>
    </div>
  )
}
