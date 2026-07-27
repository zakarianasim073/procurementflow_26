interface Award {
  awardDate: string
  tender: string
  agency: string
  category: string
  value: number
  status: 'completed' | 'in-progress' | 'cancelled'
}

interface AwardHistoryProps {
  awards?: Award[]
}

export function AwardHistory({ awards = [] }: AwardHistoryProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Recent Awards</h3>
      {awards.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No awards found</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-3 py-2 text-left font-semibold text-gray-900 dark:text-white">Date</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-900 dark:text-white">Tender</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-900 dark:text-white">Agency</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-900 dark:text-white">Category</th>
                <th className="px-3 py-2 text-right font-semibold text-gray-900 dark:text-white">Value</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-900 dark:text-white">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {awards.map((award, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-900/50">
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{award.awardDate}</td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{award.tender}</td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{award.agency}</td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{award.category}</td>
                  <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300 tabular-nums">
                    {(award.value / 1e7).toFixed(1)}Cr
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-block rounded px-2 py-1 text-xs font-medium ${
                        award.status === 'completed'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                          : award.status === 'in-progress'
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
                            : 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
                      }`}
                    >
                      {award.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
