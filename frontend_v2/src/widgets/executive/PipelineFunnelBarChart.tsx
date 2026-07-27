import type { ExecutivePipeline } from '@entities/index'

interface PipelineFunnelBarChartProps {
  data: ExecutivePipeline
  isLoading?: boolean
}

const URGENCY_COLORS = {
  closing_7d: { bar: 'bg-red-500 dark:bg-red-600', label: 'Closing 7d' },
  closing_14d: { bar: 'bg-yellow-500 dark:bg-yellow-600', label: 'Closing 14d' },
  closing_30d: { bar: 'bg-blue-500 dark:bg-blue-600', label: 'Closing 30d' },
} as const

type UrgencyKey = keyof typeof URGENCY_COLORS

function maxClosing(a: ExecutivePipeline['agencies'][0]): number {
  return Math.max(a.closing_7d, a.closing_14d, a.closing_30d, 1)
}

export function PipelineFunnelBarChart({ data, isLoading }: PipelineFunnelBarChartProps) {
  if (isLoading) {
    return <FunnelSkeleton />
  }

  if (!data.agencies.length) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No pipeline data available. When tenders are tracked, they appear here.
        </p>
      </div>
    )
  }

  const maxVal = Math.max(...data.agencies.map(maxClosing), 1)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Pipeline Funnel</h2>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {data.total_live_tenders.toLocaleString()} live tenders
        </span>
      </div>

      {/* Visual bars */}
      <div className="space-y-2">
        {data.agencies.map((agency) => (
          <div key={agency.agency_code}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="font-medium text-gray-700 dark:text-gray-300">{agency.agency_code}</span>
              <span className="tabular-nums text-gray-500 dark:text-gray-400">
                {(agency.estimated_pipeline_value_bdt / 1e7).toFixed(1)}Cr
              </span>
            </div>
            <div className="flex h-5 gap-0.5 overflow-hidden rounded">
              {(['closing_7d', 'closing_14d', 'closing_30d'] as UrgencyKey[]).map((key) => {
                const val = agency[key]
                if (val === 0) return null
                const pct = (val / maxVal) * 100
                const color = URGENCY_COLORS[key]
                return (
                  <div
                    key={key}
                    className={`${color.bar} flex items-center justify-start px-1 text-[10px] font-medium text-white transition-all`}
                    style={{ width: `${pct}%`, minWidth: val > 0 ? 'fit-content' : undefined }}
                    title={`${color.label}: ${val}`}
                  >
                    {val > 0 && val}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
        {(['closing_7d', 'closing_14d', 'closing_30d'] as UrgencyKey[]).map((key) => (
          <span key={key} className="flex items-center gap-1.5">
            <span className={`inline-block h-2.5 w-2.5 rounded ${URGENCY_COLORS[key].bar}`} />
            {URGENCY_COLORS[key].label}
          </span>
        ))}
      </div>

      {/* Accessible table fallback (screen reader) */}
      <div className="sr-only">
        <table>
          <caption>Pipeline by agency and closing window</caption>
          <thead>
            <tr>
              <th>Agency</th>
              <th>Closing 7 days</th>
              <th>Closing 14 days</th>
              <th>Closing 30 days</th>
              <th>Pipeline Value</th>
            </tr>
          </thead>
          <tbody>
            {data.agencies.map((a) => (
              <tr key={a.agency_code}>
                <td>{a.agency_code}</td>
                <td>{a.closing_7d}</td>
                <td>{a.closing_14d}</td>
                <td>{a.closing_30d}</td>
                <td>{(a.estimated_pipeline_value_bdt / 1e7).toFixed(1)}Cr</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function FunnelSkeleton() {
  return <div className="h-48 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
}
