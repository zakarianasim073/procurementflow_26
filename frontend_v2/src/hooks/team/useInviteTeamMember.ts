import { useMutation, useQueryClient } from '@tanstack/react-query'
import { inviteTeamMember } from '@entities/team'
import type { InviteTeamMemberPayload } from '@entities/team'

export function useInviteTeamMember() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: InviteTeamMemberPayload) => inviteTeamMember(data),
    onSuccess: () => {
      // Invalidate team members to refetch
      queryClient.invalidateQueries({ queryKey: ['team', 'members'] })
    },
  })
}
