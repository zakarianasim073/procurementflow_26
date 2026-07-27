import type { TeamMemberRole } from '@entities/team'

interface Props {
  members: TeamMemberRole[]
  isLoading?: boolean
}

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-200',
  admin: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200',
  member: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
  viewer: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
}

const STATUS_COLORS: Record<string, string> = {
  active: 'text-green-600 dark:text-green-400',
  inactive: 'text-gray-400 dark:text-gray-600',
}

export function TeamMembers({ members, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 rounded-lg border border-gray-200 bg-gray-50 animate-pulse dark:border-gray-800 dark:bg-gray-800"
          />
        ))}
      </div>
    )
  }

  if (!members || members.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center dark:border-gray-600 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">No team members yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <h3 className="font-semibold text-gray-900 dark:text-white">Team Members ({members.length})</h3>
      <div className="space-y-2">
        {members.map((member) => (
          <div
            key={member.id}
            className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 dark:text-white truncate">
                  {member.full_name || member.email}
                </p>
                <div className="flex items-center gap-2 mt-1 text-xs">
                  <span className={`px-2 py-1 rounded-full font-medium ${ROLE_COLORS[member.role] || ROLE_COLORS.viewer}`}>
                    {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                  </span>
                  <span className={member.is_active ? STATUS_COLORS.active : STATUS_COLORS.inactive}>
                    {member.is_active ? '● Active' : '○ Inactive'}
                  </span>
                  <span>•</span>
                  <span className="text-gray-500 dark:text-gray-400">{member.email}</span>
                  {member.department && (
                    <>
                      <span>•</span>
                      <span className="text-gray-500 dark:text-gray-400">{member.department}</span>
                    </>
                  )}
                </div>
              </div>

              {/* More options menu would go here */}
              <button className="px-3 py-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                ⋮
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
