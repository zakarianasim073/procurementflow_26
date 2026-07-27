interface ExecutiveSummaryProps {
  text: string
  highlights?: string[]
}

export function ExecutiveSummary({ text, highlights = [] }: ExecutiveSummaryProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Executive Summary</h3>
      <p className="mb-4 text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{text}</p>
      {highlights.length > 0 && (
        <div className="mt-4 space-y-2">
          {highlights.map((highlight, idx) => (
            <p key={idx} className="text-xs text-gray-600 dark:text-gray-400">
              • {highlight}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
