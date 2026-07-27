interface Project {
  category: string
  value: number
  year: number
  status: 'completed' | 'in-progress' | 'failed'
}

interface ExperienceGraphProps {
  projects?: Project[]
}

export function ExperienceGraph({ projects = [] }: ExperienceGraphProps) {
  const _categories = Array.from(new Set(projects.map((p) => p.category)))
  const years = Array.from(new Set(projects.map((p) => p.year))).sort()

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">Experience Timeline</h3>
      {projects.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No project data available</div>
      ) : (
        <div className="space-y-4">
          {years.map((year) => {
            const yearProjects = projects.filter((p) => p.year === year)
            return (
              <div key={year}>
                <p className="mb-2 text-xs font-semibold text-gray-700 dark:text-gray-300">{year}</p>
                <div className="flex gap-2 flex-wrap">
                  {yearProjects.map((p, idx) => (
                    <div
                      key={idx}
                      className={`rounded-lg px-3 py-2 text-xs font-medium ${
                        p.status === 'completed'
                          ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : p.status === 'in-progress'
                            ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                            : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}
                      title={`${p.category}: ${(p.value / 1e7).toFixed(1)}Cr`}
                    >
                      {p.category} ({(p.value / 1e7).toFixed(0)}Cr)
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
