import { useQuery } from '@tanstack/react-query'
import { getTeam } from '@entities/team'

export function useTeam() {
  return useQuery({
    queryKey: ['team'],
    queryFn: () => getTeam(),
    staleTime: 60_000,
    retry: 1,
  })
}
