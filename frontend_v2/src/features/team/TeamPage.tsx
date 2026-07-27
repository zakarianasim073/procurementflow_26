import { useState } from 'react'
import { ScreenTemplate } from '@layouts/index'
import { useTeam, usePhase2TeamMembers } from '@hooks/index'
import { TeamMembers } from './TeamMembers'
import { InviteMember } from './InviteMember'

export function TeamPage() {
  const [showInvite, setShowInvite] = useState(false)
  const { data: team } = useTeam()
  const { data: membersData, isLoading } = usePhase2TeamMembers()

  const members = membersData ?? []
  const totalMembers = members.length

  return (
    <ScreenTemplate
      header={
        <>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Team Management</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Manage team members and permissions
          </p>
        </>
      }
      primary={
        <div className="space-y-4">
          {/* Team Info */}
          {team && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-gray-900 dark:text-white">{team.name}</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {totalMembers} of {team.max_members} members
                  </p>
                </div>
                <button
                  onClick={() => setShowInvite(!showInvite)}
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium text-sm"
                >
                  {showInvite ? 'Cancel' : '+ Invite Member'}
                </button>
              </div>
            </div>
          )}

          {/* Invite Panel */}
          {showInvite && (
            <InviteMember
              onSuccess={() => {
                setShowInvite(false)
                alert('Invitation sent successfully')
              }}
              onCancel={() => setShowInvite(false)}
            />
          )}

          {/* Team Members */}
          <TeamMembers members={members} isLoading={isLoading} />
        </div>
      }
    />
  )
}
