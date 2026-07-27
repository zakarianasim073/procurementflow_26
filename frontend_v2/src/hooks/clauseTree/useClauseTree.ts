import { useQuery } from '@tanstack/react-query'
import { getClauseTree } from '@entities/index'

export function useClauseTree() {
  return useQuery({
    queryKey: ['clauseTree'],
    queryFn: () => getClauseTree(),
    staleTime: 300_000,
    retry: 1,
  })
}
