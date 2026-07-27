import type { ReactNode } from 'react'
import clsx from 'clsx'
import { SlotErrorBoundary } from './SlotErrorBoundary'

export type SlotName = 'header' | 'kpiStrip' | 'primary' | 'aiDock' | 'trustPanel' | 'activityTimeline'

export interface ScreenTemplateProps {
  /** Screen title / breadcrumb / primary actions. Optional. */
  header?: ReactNode
  /** Horizontal row of KPI cards. Optional — omit entirely on non-metric screens. */
  kpiStrip?: ReactNode
  /** The screen's core content. The only required slot. */
  primary: ReactNode
  /** Persistent AI Dock (PFX-21). Collapses to a FAB below 768px. */
  aiDock?: ReactNode
  /** Evidence/confidence panel for the primary content's AI output (ADR-002). */
  trustPanel?: ReactNode
  /** Recent activity / audit trail for the current entity. */
  activityTimeline?: ReactNode
  /** When true, every populated slot renders a skeleton matching its geometry instead of its content. */
  isLoading?: boolean
  /** Fired when a slot's content throws; the slot degrades in place rather than crashing the screen. */
  onSlotError?: (slotName: SlotName, error: Error) => void
}

/**
 * Universal screen template: Header → KPI Strip → Primary Workspace → AI Dock → Trust Panel → Activity Timeline.
 * See docs/frontend/06_LAYOUT_SYSTEM.md. Every workspace screen in frontend_v2 renders through this component
 * (ADR-001) rather than hand-rolling its own header/stats layout.
 */
export function ScreenTemplate({
  header,
  kpiStrip,
  primary,
  aiDock,
  trustPanel,
  activityTimeline,
  isLoading = false,
  onSlotError,
}: ScreenTemplateProps) {
  // Binds a slot name to the caller's callback so each SlotErrorBoundary only needs to report `(error)`.
  const errorHandlerFor = (slotName: SlotName) =>
    onSlotError ? (error: Error) => onSlotError(slotName, error) : undefined

  return (
    <div className="flex min-h-full flex-col gap-6 lg:grid lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
      <div className="flex flex-col gap-6 lg:col-span-2">
        {header !== undefined && (
          <header className="flex flex-col gap-1">
            {isLoading ? (
              <HeaderSkeleton />
            ) : (
              <SlotErrorBoundary onError={errorHandlerFor('header')}>{header}</SlotErrorBoundary>
            )}
          </header>
        )}

        {kpiStrip !== undefined && (
          <section aria-label="Key metrics" className="overflow-x-auto">
            {isLoading ? (
              <KpiStripSkeleton />
            ) : (
              <SlotErrorBoundary onError={errorHandlerFor('kpiStrip')}>{kpiStrip}</SlotErrorBoundary>
            )}
          </section>
        )}
      </div>

      <main className="flex min-w-0 flex-col gap-6 lg:col-span-1">
        {isLoading ? (
          <PrimarySkeleton />
        ) : (
          <SlotErrorBoundary onError={errorHandlerFor('primary')}>{primary}</SlotErrorBoundary>
        )}

        {activityTimeline !== undefined && (
          <aside aria-label="Activity timeline" className="lg:hidden">
            {isLoading ? (
              <SideSkeleton />
            ) : (
              <SlotErrorBoundary onError={errorHandlerFor('activityTimeline')}>{activityTimeline}</SlotErrorBoundary>
            )}
          </aside>
        )}
      </main>

      {(trustPanel !== undefined || activityTimeline !== undefined) && (
        <div className="hidden flex-col gap-6 lg:col-start-2 lg:row-start-2 lg:flex">
          {trustPanel !== undefined && (
            <aside aria-label="Trust and evidence">
              {isLoading ? (
                <SideSkeleton />
              ) : (
                <SlotErrorBoundary onError={errorHandlerFor('trustPanel')}>{trustPanel}</SlotErrorBoundary>
              )}
            </aside>
          )}
          {activityTimeline !== undefined && (
            <aside aria-label="Activity timeline">
              {isLoading ? (
                <SideSkeleton />
              ) : (
                <SlotErrorBoundary onError={errorHandlerFor('activityTimeline')}>{activityTimeline}</SlotErrorBoundary>
              )}
            </aside>
          )}
        </div>
      )}

      {aiDock !== undefined && (
        <aside
          aria-label="AI assistant"
          className={clsx(
            // <768px: floating action button / bottom sheet. >=768px (md): inline dock.
            'fixed bottom-4 right-4 z-40 md:static md:z-auto',
            'lg:col-start-2'
          )}
        >
          {isLoading ? null : (
            <SlotErrorBoundary onError={errorHandlerFor('aiDock')}>{aiDock}</SlotErrorBoundary>
          )}
        </aside>
      )}
    </div>
  )
}

function HeaderSkeleton() {
  return (
    <div className="space-y-2">
      <div className="h-6 w-48 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
      <div className="h-4 w-72 animate-pulse rounded bg-gray-100 dark:bg-gray-800/60" />
    </div>
  )
}

function KpiStripSkeleton() {
  return (
    <div className="flex gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-24 w-48 shrink-0 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
      ))}
    </div>
  )
}

function PrimarySkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-40 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
      <div className="h-40 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
    </div>
  )
}

function SideSkeleton() {
  return <div className="h-64 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
}
