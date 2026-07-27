import { useQuery } from '@tanstack/react-query'
import { getClause } from '@entities/index'

export function useClause(clauseId: string) {
  return useQuery({
    queryKey: ['clause', clauseId],
    queryFn: () => getClause(clauseId),
    staleTime: 120_000,
    retry: 1,
    enabled: !!clauseId,
  })
}
