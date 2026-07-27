import { ArrowRight } from 'lucide-react'

export interface EngagementRow {
  company_id: string
  company_name: string
  hours_saved: number
  compliance_improvement: number
  win_rate_improvement: number
  active_users: number
  feedback_rate: number
}

interface EngagementTableProps {
  rows?: EngagementRow[]
  onRowClick?: (companyId: string) => void
}

export function EngagementTable({ rows = [], onRowClick }: EngagementTableProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-900 dark:text-white">Company</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-white">Hours Saved</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-white">Compliance ↑</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-white">Win Rate ↑</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-white">Users</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-white">Feedback</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {rows.map((row) => (
              <tr
                key={row.company_id}
                onClick={() => onRowClick?.(row.company_id)}
                className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900/50"
              >
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{row.company_name}</td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300 tabular-nums">{row.hours_saved}h</td>
                <td className="px-4 py-3 text-right">
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 text-xs font-semibold text-green-700 dark:bg-green-900/30 dark:text-green-400">
                    <ArrowRight className="h-3 w-3" />\n                    {row.compliance_improvement.toFixed(1)}%\n                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                    <ArrowRight className="h-3 w-3" />\n                    {row.win_rate_improvement.toFixed(1)}%\n                  </span>
                </td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{row.active_users}</td>
                <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{(row.feedback_rate * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && (
        <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No partners to display</div>
      )}
    </div>
  )
}
