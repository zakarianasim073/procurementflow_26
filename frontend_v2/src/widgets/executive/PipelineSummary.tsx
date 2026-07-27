import type { ExecutivePipeline } from '@entities/index'

interface PipelineSummaryProps {
  data: ExecutivePipeline
}

export function PipelineSummary({ data }: PipelineSummaryProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Pipeline by Agency</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-xs font-medium uppercase text-gray-500 dark:border-gray-700 dark:text-gray-400">
              <th className="py-2 pr-4">Agency</th>
              <th className="py-2 pr-4 text-right">Live</th>
              <th className="py-2 pr-4 text-right">Closing 7d</th>
              <th className="py-2 pr-4 text-right">Closing 14d</th>
              <th className="py-2 pr-4 text-right">Closing 30d</th>
              <th className="py-2 text-right">Pipeline Value (BDT)</th>
            </tr>
          </thead>
          <tbody>
            {data.agencies.map((a) => (
              <tr key={a.agency_code} className="border-b border-gray-100 last:border-0 dark:border-gray-800">
                <td className="py-2 pr-4 font-medium text-gray-900 dark:text-white">{a.agency_code}</td>
                <td className="py-2 pr-4 text-right tabular-nums text-gray-700 dark:text-gray-300">{a.live_tenders}</td>
                <td className="py-2 pr-4 text-right tabular-nums text-gray-700 dark:text-gray-300">{a.closing_7d}</td>
                <td className="py-2 pr-4 text-right tabular-nums text-gray-700 dark:text-gray-300">{a.closing_14d}</td>
                <td className="py-2 pr-4 text-right tabular-nums text-gray-700 dark:text-gray-300">{a.closing_30d}</td>
                <td className="py-2 text-right tabular-nums text-gray-700 dark:text-gray-300">
                  {(a.estimated_pipeline_value_bdt / 1e7).toFixed(1)}Cr
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.value_note && (
        <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">{data.value_note}</p>
      )}
    </div>
  )
}

export function PipelineSummarySkeleton() {
  return (
    <div className="h-48 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
  )
}
