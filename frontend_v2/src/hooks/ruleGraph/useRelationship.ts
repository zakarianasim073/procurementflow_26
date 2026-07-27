import { useQuery } from '@tanstack/react-query'
import { getRelationship } from '@entities/index'

export function useRelationship(source: string, target: string) {
  return useQuery({
    queryKey: ['ruleGraph', 'relationship', source, target],
    queryFn: () => getRelationship(source, target),
    staleTime: 300_000,
    retry: 1,
    enabled: !!source && !!target,
  })
}
