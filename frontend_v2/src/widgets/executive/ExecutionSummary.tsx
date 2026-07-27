interface ExecutionSummaryProps {
  eexperienceCompleted: number
  ecmsOngoing: number
  eexperienceValueBdt: number
  ecmsValueBdt: number
}

export function ExecutionSummary({
  eexperienceCompleted,
  ecmsOngoing,
  eexperienceValueBdt,
  ecmsValueBdt,
}: ExecutionSummaryProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Execution Overview</h2>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Completed (eExperience)</p>
          <p className="text-xl font-bold tabular-nums text-gray-900 dark:text-white">{eexperienceCompleted.toLocaleString()}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Value: {(eexperienceValueBdt / 1e7).toFixed(1)}Cr BDT
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Ongoing (eCMS)</p>
          <p className="text-xl font-bold tabular-nums text-gray-900 dark:text-white">{ecmsOngoing.toLocaleString()}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Value: {(ecmsValueBdt / 1e7).toFixed(1)}Cr BDT
          </p>
        </div>
      </div>
    </div>
  )
}

export function ExecutionSummarySkeleton() {
  return (
    <div className="h-28 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
  )
}
