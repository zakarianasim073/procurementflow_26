import { useQuery } from '@tanstack/react-query'
import { getRuleGraph } from '@entities/index'

export function useRuleGraph() {
  return useQuery({
    queryKey: ['ruleGraph'],
    queryFn: () => getRuleGraph(),
    staleTime: 300_000,
    retry: 1,
  })
}
