import { useQuery } from '@tanstack/react-query'
import { getPprRules } from '@entities/index'

export function usePprRules(category?: string) {
  return useQuery({
    queryKey: ['intelligence', 'ppr-rules', category],
    queryFn: () => getPprRules(category),
    staleTime: 300_000,
    retry: 1,
  })
}
