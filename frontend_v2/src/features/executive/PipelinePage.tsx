import { Link } from 'react-router-dom'
import { ArrowLeft, AlertTriangle, Clock } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { useExecutivePipeline } from '@hooks/index'
import { PipelineFunnelBarChart } from '@widgets/executive/index'

interface UrgentAction {
  id: number
  title: string
  agency: string
  tender_id: string
  urgency: 'high' | 'medium'
  closing: string
  days_left: number
}

function UrgentActionsPanel({ data, isLoading }: { data: ReturnType<typeof useExecutivePipeline>['data']; isLoading: boolean }) {
  if (isLoading) return <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}</div>
  if (!data?.agencies.length) return null

  const actions: UrgentAction[] = data.agencies.flatMap((a, idx) => {
    const items: UrgentAction[] = []
    if (a.closing_7d > 0) items.push({ id: idx * 3 + 1, title: `${a.closing_7d} tenders closing`, agency: a.agency_code, tender_id: '', urgency: 'high' as const, closing: '7 days', days_left: 7 })
    if (a.closing_14d > 0) items.push({ id: idx * 3 + 2, title: `${a.closing_14d} tenders closing soon`, agency: a.agency_code, tender_id: '', urgency: 'medium' as const, closing: '14 days', days_left: 14 })
    return items
  }).sort((a, b) => a.days_left - b.days_left).slice(0, 8)

  if (!actions.length) return <p className="text-sm text-gray-400 py-4 text-center">No urgent actions</p>

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
        <AlertTriangle size={14} /> Urgent Actions
      </h2>
      <div className="space-y-2">
        {actions.map(a => (
          <div key={a.id} className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
            <div className={cn(
              'flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
              a.urgency === 'high' ? 'bg-red-100 dark:bg-red-900/40' : 'bg-yellow-100 dark:bg-yellow-900/40'
            )}>
              <Clock size={12} className={a.urgency === 'high' ? 'text-red-600' : 'text-yellow-600'} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 dark:text-white">{a.title}</p>
              <p className="text-xs text-gray-500">{a.agency} · {a.closing}</p>
            </div>
            <span className={cn(
              'shrink-0 rounded px-2 py-0.5 text-[10px] font-medium',
              a.urgency === 'high' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400' : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400'
            )}>{a.urgency}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function PipelinePage() {
  const pipeline = useExecutivePipeline()
  const data = pipeline.data

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <Link to="/executive" className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300">
            <ArrowLeft size={18} />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Pipeline</h1>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
              {data ? `${data.total_live_tenders.toLocaleString()} live tenders across ${data.agencies.length} agencies` : 'Loading...'}
            </p>
          </div>
        </div>
      }
      kpiStrip={
        data ? (
          <div className="grid grid-cols-4 gap-3">
            <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
              <p className="text-xs text-gray-500">Live Tenders</p>
              <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{data.total_live_tenders.toLocaleString()}</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
              <p className="text-xs text-gray-500">Pipeline Value</p>
              <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{((data as any).total_pipeline_value_bdt / 1e7).toFixed(1)}Cr</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
              <p className="text-xs text-gray-500">Closing &lt;7d</p>
              <p className="mt-1 text-lg font-bold text-red-600">{data.agencies.reduce((s, a) => s + a.closing_7d, 0)}</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
              <p className="text-xs text-gray-500">Agencies</p>
              <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{data.agencies.length}</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
          </div>
        )
      }
      primary={
        <div className="space-y-4">
          {pipeline.isLoading ? (
            <Skeleton className="h-64 w-full rounded-xl" />
          ) : data ? (
            <PipelineFunnelBarChart data={data} />
          ) : null}
        </div>
      }
      aiDock={
        <UrgentActionsPanel data={data} isLoading={pipeline.isLoading} />
      }
      activityTimeline={
        data && data.agencies.length > 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
            <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Agency Breakdown</h2>
            <div className="space-y-2">
              {data.agencies.slice(0, 8).map(a => (
                <div key={a.agency_code} className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{a.agency_code}</span>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span className="tabular-nums">{a.closing_7d}d</span>
                    <span className="tabular-nums">{a.closing_14d}d</span>
                    <span className="tabular-nums">{(a.estimated_pipeline_value_bdt / 1e7).toFixed(1)}Cr</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null
      }
    />
  )
}
