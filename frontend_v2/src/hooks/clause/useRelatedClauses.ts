import { useQuery } from '@tanstack/react-query'
import { getRelatedClauses } from '@entities/index'

export function useRelatedClauses(clauseId: string) {
  return useQuery({
    queryKey: ['clauses', clauseId, 'related'],
    queryFn: () => getRelatedClauses(clauseId),
    staleTime: 120_000,
    retry: 1,
    enabled: !!clauseId,
  })
}
