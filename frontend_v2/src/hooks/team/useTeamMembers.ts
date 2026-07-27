import { useQuery } from '@tanstack/react-query'
import { listTeamMembers } from '@entities/team'

export function useTeamMembers() {
  return useQuery({
    queryKey: ['team', 'members'],
    queryFn: () => listTeamMembers(),
    staleTime: 30_000,
    retry: 1,
  })
}
