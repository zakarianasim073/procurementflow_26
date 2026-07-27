import { useQuery } from '@tanstack/react-query'
import { getRecentAgentResults } from '@entities/index'

export function useRecentAgentResults(limit = 10) {
  return useQuery({
    queryKey: ['opportunity', 'agent-results', limit],
    queryFn: () => getRecentAgentResults(limit),
    staleTime: 30_000,
    retry: 1,
  })
}
